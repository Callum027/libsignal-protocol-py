#
# Signal Protocol Python library
# pysignal/__init__.py - library public classes and methods
#
# Copyright (c) 2017 Catalyst.net Ltd
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


'''
Signal Protocol Python library.
'''


import datetime
import io
import re
import shutil
import subprocess
import threading

from pysignal.exception import SignalCLIError
from pysignal.exception import ReceiptNotFoundError


SIGNAL_CLI = shutil.which("signal-cli")


class Signal(object):
    '''
    '''


    def __init__(self, username, signal_cli=SIGNAL_CLI):
        '''
        '''

        self.username = username # Says username, is actually user's registered phone number.
        self.signal_cli = signal_cli

        self.lock = threading.Lock()


    #
    ##
    #


    def signal_cli_call(self, *args, username=self.username, timeout=60):
        '''
        '''

        process_args = [self.signal_cli]
        process_args.extend(args)
        process_args.extend(["-u", username])

        try:
            process = subprocess.Popen(
                process_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(30)

            if process.returncode != 0:
                raise SignalCLIError(process.returncode, stderr)

            return (stdout, stderr)

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise RuntimeError(
                "timeout reached ({} seconds)\n\nstdout:\n{}\n\nstderr:\n{}".format(
                    timeout,
                    stdout,
                    stderr,
                ),
            )

        except subprocess.CalledProcessError:
            raise # TODO: handle appropriately



    #
    ## Receiving methods.
    #


    def receive(self):
        '''
        Receive all unread messages from Signal and return them.

        This method is blocking, and cannot be used concurrently with other threads
        attempting to run receive() or send().
        '''

        self.lock.acquire(blocking=True)

        try:
            return self.receive_messages_get()
        finally:
            self.lock.release()


    def receive_messages_get(self):
        '''
        '''

        return Signal.messages_read(self.signal_cli_call("receive"))


    # pylint: disable=too-many-branches
    @staticmethod
    def messages_read(data):
        '''
        '''

        messages = []
        data_stream = io.StringIO(data)

        current_message = {}

        while True:
            line = data_stream.readline()

            if line == "":
                break

            if not current_message:
                if line.startswith("Envelope from"):
                    result = re.match(r"^Envelope from: (\+[0-9]+) \(device: ([0-9]+)\)$", line)
                    current_message = {
                        "number": result.group(1),
                        "device": int(result.group(2)),
                        "timestamp": None,
                        "message_timestamp": None,
                        "receipt": False,
                        "body": None,
                    }
                else:
                    raise RuntimeError(
                        "found an 'Envelope from' line "
                        "while processing a previous message",
                    )

            else: # current_message is not empty
                # Empty line signals end of last message.
                if line == "\n":
                    messages.append(current_message)
                    current_message = {}

                elif line.startswith("Timestamp"):
                    result = re.match(
                        # pylint: disable=line-too-long
                        r"^Timestamp: ([0-9]+) \([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9][0-9][0-9]Z\)$",
                        line,
                    )
                    current_message["timestamp"] = int(result.group(1))

                elif line.startswith("Message timestamp"):
                    result = re.match(
                        # pylint: disable=line-too-long
                        r"^Message timestamp: ([0-9]+) \([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9][0-9][0-9]Z\)$",
                        line,
                    )
                    current_message["message_timestamp"] = int(result.group(1))

                elif line.strip("\n") == "Got receipt.":
                    if current_message["body"] is not None:
                        # raise a stink
                        raise RuntimeError(
                            "current_message[\"body\"] is not None "
                            "but current_message[\"receipt\"] will be set to True"
                        )
                    current_message["receipt"] = True

                elif line.startswith("Body"):
                    if current_message["receipt"] is True:
                        raise RuntimeError(
                            "current_message[\"receipt\"] is True "
                            "but current_message[\"body\"] will have data put in it"
                        )
                    current_message["body"] = re.sub(r"^Body: ", "", line).strip("\n")

        # Finalise last message.
        if current_message:
            messages.append(current_message)
            current_message = {}

        return messages


    #
    ## Sending methods.
    #


    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    def send(self, message,
             recipient=None, recipients=None,
             attachment=None, attachments=None,
             verify_receipt=False):
        '''
        Send a message to Signal to be sent to the given recipients.

        If verify_receipt is True, keep reading messages back until a receipt is found,
        and return unhandled messages to the caller.

        This method is not blocking if verify_receipt is False, but IS if it is True,
        and in this case cannot be used concurrently with other threads attempting to
        run receive() or send().
        '''

        # TODO: incorporate error checking for this
        # ./signal-cli -u +61481073042 send -m "Test Message 02" +64220908052
        # Failed to send (some) messages:
        # Untrusted Identity for "+64220908052": Untrusted identity key!

        # * Allow more than one recipient and attachment to be specified.
        # * Take a timestamp of when the message was sent, look for the first receipt for
        #   AFTER this timestamp. This makes sure this method does not get confused when
        #   previous (unchecked) receipts are found.

        self.lock.acquire(blocking=verify_receipt)

        unhandled_messages = []

        try:
            # Prepare the signal-cli arguments.
            args = ["send", "-m", message]
            if attachments is not None:
                args.append("-a")
                args.extend(attachments)
            else:
                args.extend(["-a", attachment])
            if recipients is not None:
                args.extend(recipients)
            else:
                args.append(recipient)

            # Get an approximate time we sent the message.
            timestamp = (datetime.datetime.utcnow() * 1000.0).timestamp()

            # Call signal-cli to send the message.
            self.signal_cli_call(*args)

            # TODO: Try and find a better way to implement this... if possible.
            #
            # Read stored messages from Signal until the "arrival receipt" is found.
            # Save unrelated messages to be returned to the caller later.
            #
            # Look for receipt messages, match up the timestamps. If we have a match,
            # whoo!
            if verify_receipt:
                receipt_verified = False
                while not receipt_verified:
                    messages = self.receive_messages_get()
                    receipts = [message for message in messages if message["receipt"]]
                    sorted_receipts = sorted(receipts, key=lambda x: x["timestamp"])
                    for receipt in sorted_receipts:
                        if receipt["timestamp"] < timestamp:
                            continue
                        # If we reach this point, we've found the first receipt
                        # timestamped AFTER ours, which we may safely assume to be
                        # receipt for this message.
                        receipt_verified = True
                        # TODO: finish

        finally:
            self.lock.release()

        return unhandled_messages


    #
    ##
    #


    def safety_number_verify(self):
        '''
        '''

        # TODO: Locking?
        # self.lock.acquire(blocking=True)
        # try:

        # List identities.
        identities = Signal.identities_read(self.signal_cli_call("listIdentities"))

        # TODO: Verify.
        for identity in identities:
            if identity["status"] == "UNTRUSTED":
                # Untrusted. What to do in this case?
                continue
            elif identity["status"] == "TRUSTED_UNVERIFIED":
                # Trusted but unverified, needs to be verified with user input?
                continue
            elif identity["status"] == "TRUSTED_VERIFIED":
                # Trusted and verified identity. No need to do anything.
                continue

        # finally:
        #   self.lock.release()


    @staticmethod
    def identities_read(data):
        '''
        '''

        identities = []
        data_stream = io.StringIO(data)

        while True:
            line = data_stream.readline()

            if line == "":
                break

            # pylint: disable=line-too-long
            result = re.match(r"^(\+[0-9]+): (UNTRUSTED|TRUSTED_UNVERIFIED|TRUSTED_VERIFIED) Added: ((Mon|Tue|Wed|Thu|Fri) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [0-9][0-9]? [0-9]{2}:[0-9]{2}:[0-9]{2} [^\s]+ [0-9]+) Fingerprint: ([0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2})  Safety Number: ([0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5})$", line)

            identities.append({
                "number": result.group(1),
                "status": result.group(2),
                "added_date": result.group(3),
                "fingerprint": result.group(6),
                "safety_number": result.group(7),
            })

        return identities

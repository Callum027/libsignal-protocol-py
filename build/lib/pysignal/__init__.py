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
    ## Message methods.
    #


    def messages_read(self, data):
        '''
        '''

        # Envelope from: +64275263733 (device: 1)
        # Timestamp: 1511746018074 (2017-11-27T01:26:58.074Z)
        # Got receipt.

        # Envelope from: +64275263733 (device: 1)
        # Timestamp: 1511746064589 (2017-11-27T01:27:44.589Z)

        # Envelope from: +64275263733 (device: 1)
        # Timestamp: 1511746101590 (2017-11-27T01:28:21.590Z)
        # Message timestamp: 1511746101590 (2017-11-27T01:28:21.590Z)
        # Body: Hddhfjfjfjfjffigf

        messages = []
        data_stream = io.StringIO(data)

        current_message = None

        while True:
            line = data_stream.readline()

            if line == "":
                break

            if current_message is None:
                if line.startswith("Envelope from"):
                    result = re.match("^Envelope from: (\+[0-9]+) \(device: ([0-9]+)\)$", line)
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

            else:
                # Empty line signals end of last message.
                if line == "\n" and current_message is not None:
                    messages.append(current_message)
                    current_message = None

                elif line.startswith("Timestamp"):
                    result = re.match(
                        "^Timestamp: ([0-9]+) "
                        "\([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
                        "T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9][0-9][0-9]Z\)$",
                        line,
                    )
                    current_message["timestamp"] = int(result.group(1))

                elif current_message is not None and line.startswith("Message timestamp"):
                    result = re.match(
                        "^Message timestamp: ([0-9]+) "
                        "\([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
                        "T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9][0-9][0-9]Z\)$",
                        line,
                    )
                    current_message["message_timestamp"] = int(result.group(1))

                elif current_message is not None and line.strip("\n") == "Got receipt.":
                    if current_message["body"] is not None:
                        # raise a stink
                        raise RuntimeError(
                            "current_message[\"body\"] is not None "
                            "but current_message[\"receipt\"] will be set to True"
                        )
                    current_message["receipt"] = True

                elif current_message is not None and line.startswith("Body"):
                    if current_message["receipt"] is True:
                        raise RuntimeError(
                            "current_message[\"receipt\"] is True "
                            "but current_message[\"body\"] will have data put in it"
                        )
                    current_message["body"] = re.sub("^Body: ", "", line).strip("\n")

        # Finalise last message.
        if current_message is not None:
            messages.append(current_message)
            current_message = None

        return messages


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
        messages = self._receive(self)
        self.lock.release()

        return messages


    def _receive(self):
        '''
        '''

        try:
            process = subprocess.Popen(
                [self.signal_cli, "receive", "-u", self.username],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(60)

            if process.returncode != 0:
                # TODO: error handling stuff
                pass

            return self.messages_read(stdout)

        except TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            # TODO: handle error appropriately for timing out

        except CalledProcessError:
            pass # TODO: handle appropriately


    #
    ## Sending methods.
    #


    def send(self, message,
             recipient=None, recipients=None,
             attachment=None, attachments=None,
             group=None, verify_receipt=False):
        '''
        Send a message to Signal to be sent to the given recipients.

        If verify_receipt is True, keep reading messages back until a receipt is found,
        and return unhandled messages to the caller.

        This method is not blocking if verify_receipt is False, but IS if it is True,
        and in this case cannot be used concurrently with other threads attempting to
        run receive() or send().
        '''

        # * Allow more than one recipient and attachment to be specified.
        # * Take a timestamp of when the message was sent, look for the first receipt for
        #   AFTER this timestamp. This makes sure this method does not get confused when
        #   previous (unchecked) receipts are found.

        self.lock.acquire(blocking=verify_receipt)

        unhandled_messages = []

        try:
            process = None

            # Send the message.
            args = [self.signal_cli, "send", "-u", self.username, "-m", message]

            if attachments is not None:
                args.append("-a")
                args.extend(attachments)
            else:
                args.extend(["-a", attachment])

            if recipients is not None:
                args.extend(recipients)
            else:
                args.append(recipient)

            try:
                process = subprocess.Popen(
                    args,
                    stderr=subprocess.PIPE,
                )
                process.wait(30)

                if process.returncode != 0:
                    pass # TODO: error handling stuff

            except TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                # TODO: handle error appropriately for timing out

            except CalledProcessError:
                pass # TODO: handle appropriately

            # Read stored messages from Signal until the "arrival receipt" is found.
            # Save unrelated messages to be returned to the caller later.
            #
            # Look for receipt messages, match up the timestamps. If we have a match,
            # whoo!
            for message in self._receive():
                pass # TODO: finish

        finally:
            self.lock.release()

        return unhandled_messages


    def send_get_prekey(self, recipient):
        '''
        Helper method for send() to fetch the prekeys for the given recipient.
        '''

        if recipient in send_prekeys:
            return send_prekeys[recipient]

        obj = self.api_call(
            requests.get,
            "/".join(self.endpoint, "keys", recipient, "*"),
            recipient=recipient,
        )

        prekeys = {}
        for data in obj["keys"]:
            prekeys[data["deviceId"]] = {
                "keyId": data["keyId"],
                "publicKey": data["publicKey"],
                "identityKey": data["identityKey"],
            }

        self.send_prekeys[recipient] = prekeys
        return prekeys


    #
    ## Attachment methods.
    #


    def attachment_allocate(self):
        '''
        Allocate a unique attachment ID, and return that and its corresponding URL.

        This method is not blocking, and is unaffected by the receive/send lock.
        '''

        # ...

        return (attachment_id, attachment_url)


    def attachment_upload(self, attachment_id, data):
        '''
        Upload data to the given attachment ID's location.

        This method is not blocking, and is unaffected by the receive/send lock.
        '''

        pass


    def attachment_retrieve(self, attachment_id):
        '''
        Retrieve data from the given attachment ID.

        This method is not blocking, and is unaffected by the receive/send lock.
        '''

        # ...

        return data

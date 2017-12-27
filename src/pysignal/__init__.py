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

        try:
            return self._receive(self)

        finally:
            self.lock.release()


    def _receive(self):
        '''
        '''

        # TODO: add attachment support.

        try:
            process = subprocess.Popen(
                [self.signal_cli, "receive", "-u", self.username],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(60)

            if process.returncode != 0:
                raise SignalCLIError(process.returncode, stderr)

            return self.messages_read(stdout)

        except TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise RuntimeError(
                "timeout reached (60 seconds)\n\nstdout:\n{}\n\nstderr:\n{}".format(stdout, stderr),
            )

        except CalledProcessError:
            raise # TODO: handle appropriately


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

        #root@cat-wlgwil-test-hotpotato2:/root/signal-cli-0.5.6/bin# ./signal-cli -u +61481073042 send -m "Test Message 02" +64220908052
        #Failed to send (some) messages:
        #Untrusted Identity for "+64220908052": Untrusted identity key!

        # * Allow more than one recipient and attachment to be specified.
        # * Take a timestamp of when the message was sent, look for the first receipt for
        #   AFTER this timestamp. This makes sure this method does not get confused when
        #   previous (unchecked) receipts are found.

        self.lock.acquire(blocking=verify_receipt)

        unhandled_messages = []

        try:
            process = None

            # Prepare the signal-cli arguments.
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

            # Get an approximate time we sent the message.
            timestamp = (datetime.datetime.utcnow() * 1000.0).timestamp()

            # Call signal-cli to send the message.
            try:
                process = subprocess.Popen(
                    args,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = process.communicate(30)
                if process.returncode != 0:
                    raise SignalCLIError(process.returncode, stderr)
            except TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                # TODO: handle error appropriately for timing out
            except CalledProcessError:
                raise # TODO: handle appropriately

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
                    messages = self._receive()
                    receipts = [message for message in messages if message["receipt"]]
                    sorted_receipts = sorted(receipts, key=lambda x: x["timestamp"])
                    for receipt in sorted_receipts:
                        if receipt["timestamp"] < timestamp:
                            continue
                        # If we reach this point, we've found the first receipt
                        # timestamped AFTER ours, which we may safely assume to be
                        # receipt for this message.
                        receipt_verified = True
                        pass # TODO: finish

        finally:
            self.lock.release()

        return unhandled_messages


    #
    ##
    #


    def safety_number_verify(self, safety_number):
        '''
        '''

        # TODO
        #root@cat-wlgwil-test-hotpotato2:/root/signal-cli-0.5.6/bin# time ./signal-cli -u +61481073042 listIdentities
        #+64275263733: TRUSTED_UNVERIFIED Added: Mon Nov 27 13:14:40 NZDT 2017 Fingerprint: 05 44 df fe 10 ec 38 47 d1 b5 14 79 37 ab 9e 1c 8a e5 37 d6 1e b6 8b 16 72 cf da 6e 97 9e 42 c3 33  Safety Number: 15778 20682 42583 15572 36500 86531 74249 00584 14631 26803 60323 14180
        #+64224307685: TRUSTED_VERIFIED Added: Mon Nov 27 14:45:32 NZDT 2017 Fingerprint: 05 c6 cb 14 b9 b8 1b db af 92 3f f0 bb a4 36 92 f8 43 a6 78 30 94 3b fb 4b 7a a4 db 1c d6 3e 9e 62  Safety Number: 60455 13090 15565 16601 14619 41766 74249 00584 14631 26803 60323 14180
        #+64220908052: TRUSTED_UNVERIFIED Added: Tue Nov 28 10:09:09 NZDT 2017 Fingerprint: 05 e6 ac fb ad fe b0 7d dd df ca f9 c3 29 db 14 34 7a fa 45 18 1a 68 9c a3 54 2d fa 99 c3 a0 47 08  Safety Number: 74249 00584 14631 26803 60323 14180 89548 91050 80140 81284 06917 18989
        #
        #real    0m2.921s
        #user    0m2.792s
        #sys     0m0.116s
        #root@cat-wlgwil-test-hotpotato2:/root/signal-cli-0.5.6/bin# time ./signal-cli -u +61481073042 trust -v "74249 00584 14631 26803 60323 14180 89548 91050 80140 81284 06917 18989" +64220908052
        #
        #real    0m4.261s
        #user    0m3.124s
        #sys     0m0.140s
        #root@cat-wlgwil-test-hotpotato2:/root/signal-cli-0.5.6/bin# time ./signal-cli -u +61481073042 listIdentities
        #+64275263733: TRUSTED_UNVERIFIED Added: Mon Nov 27 13:14:40 NZDT 2017 Fingerprint: 05 44 df fe 10 ec 38 47 d1 b5 14 79 37 ab 9e 1c 8a e5 37 d6 1e b6 8b 16 72 cf da 6e 97 9e 42 c3 33  Safety Number: 15778 20682 42583 15572 36500 86531 74249 00584 14631 26803 60323 14180
        #+64224307685: TRUSTED_VERIFIED Added: Mon Nov 27 14:45:32 NZDT 2017 Fingerprint: 05 c6 cb 14 b9 b8 1b db af 92 3f f0 bb a4 36 92 f8 43 a6 78 30 94 3b fb 4b 7a a4 db 1c d6 3e 9e 62  Safety Number: 60455 13090 15565 16601 14619 41766 74249 00584 14631 26803 60323 14180
        #+64220908052: TRUSTED_VERIFIED Added: Tue Nov 28 10:09:09 NZDT 2017 Fingerprint: 05 e6 ac fb ad fe b0 7d dd df ca f9 c3 29 db 14 34 7a fa 45 18 1a 68 9c a3 54 2d fa 99 c3 a0 47 08  Safety Number: 74249 00584 14631 26803 60323 14180 89548 91050 80140 81284 06917 18989
        #root@cat-wlgwil-test-hotpotato2:/root/signal-cli-0.5.6/bin# time ./signal-cli -u +61481073042 listIdentities
        #+64275263733: TRUSTED_UNVERIFIED Added: Mon Nov 27 13:14:40 NZDT 2017 Fingerprint: 05 44 df fe 10 ec 38 47 d1 b5 14 79 37 ab 9e 1c 8a e5 37 d6 1e b6 8b 16 72 cf da 6e 97 9e 42 c3 33  Safety Number: 15778 20682 42583 15572 36500 86531 74249 00584 14631 26803 60323 14180
        #+64224307685: TRUSTED_VERIFIED Added: Mon Nov 27 14:45:32 NZDT 2017 Fingerprint: 05 c6 cb 14 b9 b8 1b db af 92 3f f0 bb a4 36 92 f8 43 a6 78 30 94 3b fb 4b 7a a4 db 1c d6 3e 9e 62  Safety Number: 60455 13090 15565 16601 14619 41766 74249 00584 14631 26803 60323 14180
        #+64220908052: TRUSTED_VERIFIED Added: Tue Nov 28 10:09:09 NZDT 2017 Fingerprint: 05 e6 ac fb ad fe b0 7d dd df ca f9 c3 29 db 14 34 7a fa 45 18 1a 68 9c a3 54 2d fa 99 c3 a0 47 08  Safety Number: 74249 00584 14631 26803 60323 14180 89548 91050 80140 81284 06917 18989
        #+64220908052: UNTRUSTED Added: Tue Nov 28 10:12:50 NZDT 2017 Fingerprint: 05 f4 82 48 c2 b8 79 81 24 80 f7 b9 1d d8 fa c9 3e bd ec c3 76 9e d6 b0 54 a2 b1 d1 99 b6 eb ee 22  Safety Number: 74249 00584 14631 26803 60323 14180 77508 56318 57208 29012 65010 43730

        # Call signal-cli to send the message.
        try:
            # List identities.
            process = subprocess.Popen(
                [self.signal_cli, "listIdentities", "-u", self.username],
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(30)
            if process.returncode != 0:
                raise SignalCLIError(process.returncode, stderr)

            

            

            # Verify.
            for safety_number in safety_numbers:
                process = subprocess.Popen(
                    [self.signal_cli, "listIdentities", "-u", self.username],
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = process.communicate(30)
                if process.returncode != 0:
                    raise SignalCLIError(process.returncode, stderr)
        except TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            # TODO: handle error appropriately for timing out
        except CalledProcessError:
            raise # TODO: handle appropriately


    def identities_read(self, data):
        '''
        '''

        # +64275263733: TRUSTED_UNVERIFIED Added: Mon Nov 27 13:14:40 NZDT 2017 Fingerprint: 05 44 df fe 10 ec 38 47 d1 b5 14 79 37 ab 9e 1c 8a e5 37 d6 1e b6 8b 16 72 cf da 6e 97 9e 42 c3 33  Safety Number: 15778 20682 42583 15572 36500 86531 74249 00584 14631 26803 60323 14180
        # +64224307685: TRUSTED_VERIFIED Added: Mon Nov 27 14:45:32 NZDT 2017 Fingerprint: 05 c6 cb 14 b9 b8 1b db af 92 3f f0 bb a4 36 92 f8 43 a6 78 30 94 3b fb 4b 7a a4 db 1c d6 3e 9e 62  Safety Number: 60455 13090 15565 16601 14619 41766 74249 00584 14631 26803 60323 14180
        # +64220908052: TRUSTED_VERIFIED Added: Tue Nov 28 10:09:09 NZDT 2017 Fingerprint: 05 e6 ac fb ad fe b0 7d dd df ca f9 c3 29 db 14 34 7a fa 45 18 1a 68 9c a3 54 2d fa 99 c3 a0 47 08  Safety Number: 74249 00584 14631 26803 60323 14180 89548 91050 80140 81284 06917 18989
        # +64220908052: UNTRUSTED Added: Tue Nov 28 10:12:50 NZDT 2017 Fingerprint: 05 f4 82 48 c2 b8 79 81 24 80 f7 b9 1d d8 fa c9 3e bd ec c3 76 9e d6 b0 54 a2 b1 d1 99 b6 eb ee 22  Safety Number: 74249 00584 14631 26803 60323 14180 77508 56318 57208 29012 65010 43730

        identities = []
        data_stream = io.StringIO(data)

        while True:
            line = data_stream.readline()

            if line == "":
                break

            result = re.match("^(\+[0-9]+): (UNTRUSTED|TRUSTED_UNVERIFIED|TRUSTED_VERIFIED) Added: ((Mon|Tue|Wed|Thu|Fri) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [0-9][0-9]? [0-9]{2}:[0-9]{2}:[0-9]{2} [^\s]+ [0-9]+) Fingerprint: ([0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2})  Safety Number: ([0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5} [0-9]{5})$", line)

            identities.append({
                "number": result.group(1),
                "status": result.group(2),
                "added_date": result.group(3),
                "fingerprint": result.group(6),
                "safety_number": result.group(7),
            })

        return identities

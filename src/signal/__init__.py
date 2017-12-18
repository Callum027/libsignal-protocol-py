#
# Signal Protocol Python library
# signal/__init__.py - library public classes and methods
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
import subprocess
import threading

from signal import util

from signal.exception import ReceiptNotFoundError


class Signal(object):
    '''
    '''


    def __init__(self, username, signal_cli=SIGNAL_CLI):
        '''
        '''

        self.username = username # Says username, is actually user's registered phone number.

        self.lock = threading.Lock()


    #
    ## Receiving methods.
    #


    def _receive(self):
        '''
        '''

        


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


    #
    ##
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
        for line in data_stream.readline(): 
            if current_message is None and line.startswith("Envelope from"):
                result = re.match("^Envelope from: (\+[0-9]+) \(device: ([0-9]+)\)$")
                current_message = {
                    "number": result.group(1),
                    "device": result.group(2),
                    "timestamp": None,
                    "message_timestamp": None,
                    "receipt": False,
                    "body": None,
                }
            elif current_message is not None and line.startswith("Timestamp"):
                result = re.match(
                    "^Timestamp: ([0-9]+) "
                    "\([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
                    "T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9][0-9][0-9]Z\)$"
                )
                current_message["timestamp"] = datetime.utcfromtimestamp(
                    int(result.group(1)),
                )
            elif current_message is not None and line.startswith("Message timestamp"):
                result = re.match(
                    "^Message timestamp: ([0-9]+) "
                    "\([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"
                    "T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9][0-9][0-9]Z\)$"
                )
                current_message["message_timestamp"] = datetime.utcfromtimestamp(
                    int(result.group(1)),
                )
            elif current_message is not None and line == "Got receipt.":
                if current_message["body"] is not None:
                    # raise a stink
                    raise RuntimeError(
                        "current_message[\"body\"] is not None "
                        "but current_message[\"receipt\"] will be set to True"
                    )
                current_message["receipt"] = True
            elif current_message is not None and line.startswith("Body"):
                if current_message["receipt"] is True:
                    # raise a stink
                    raise RuntimeError(
                        "current_message[\"receipt\"] is True "
                        "but current_message[\"body\"] will have data put in it"
                    )
                current_message["data"] = re.sub("^Body: ", "", data)

        return messages


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
            args = [self.signal_cli, "send", "-u", username, "-m", message]

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
                    # error handling stuff
            except CalledProcessError:
                pass # ...

            # Read stored messages from Signal until the "arrival receipt" is found.
            # Save unrelated messages to be returned to the caller later.
            try:
                process = subprocess.Popen(
                    [self.signal_cli, "receive", "-u", username],
                    stdin=subprocess.PIPE
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = process.communicate(60)

                if process.returncode != 0:
                    # error handling stuff

                messages = self.messages_read(stdout)

                # Look for receipt messages, match up the timestamps. If we have a match,
                # whoo!

            except TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()

            except CalledProcessError:
                pass # ...

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

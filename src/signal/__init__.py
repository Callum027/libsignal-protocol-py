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

        try:
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
            except CallledProcessError:
                pass # ...

        finally:
            self.lock.release()

        # Check error code.

        process.stdin

        if (process.stderr)

        try:
            # TODO: group stuff
            recs = list(recipient) if isinstance(recipient, list) else [recipient]
            group_contexts = None # list of GroupContext

            # Upload attachments, and get their IDs and content types.
            attachment_pointers = None # list of AttachmentPointer

            flags = None # PushMessageContent.Flag (END_SESSION)

            for rec in recs:
                prekeys = self.send_get_prekey(recipient)        

                # Decide what device to go with.

                for device_id, key_info in prekeys.items():
                    # TODO: CONTINUE HERE
                    current_time_millis = datetime.datetime.utcnow() * 1000.0
                    timestamp = current_time_millis.timestamp() 

                    body = PushMessageContent(
                        body=message,
                        attachments=attachment_pointers,
                        groups=group_contexts,
                        flags=flags,
                    ).to_base64()

                    # encrypt body

                    obj = self.api_call(
                        requests.get,
                        "/".join(self.endpoint, "messages", recipient),
                        data={
                            "messages": [
                                {
                                    "type": ,
                                    "destinationDeviceId": device_id,
                                    "destinationRegistrationId": ,
                                    "body": , # "{base64_encoded_message_body}", // Encrypted PushMessageContent
                                    "timestamp": timestamp,
                                },
                            ],
                        },
                        recipient=recipient,
                    )

                response = requests.post(
                    uri,
                    auth=HTTPTokenAuth(self.token) if self.token else None,
                    verify=self.api_ssl_verify,
                )
        finally:

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

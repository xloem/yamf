import datetime, json, os, sys#, imaplib
import imapclient

#import logging
#logging.basicConfig(level=logging.DEBUG)

try:
    import yamf_config as cfg
except:
    print('''
yamf_config.py:
host = 'mailhost'
port = 'port'
ssl = True

user = 'username'
pw = 'password'

pattern = '*' # mailboxes to match
''')
    raise

class IMAPJSONEncoder(json.JSONEncoder):
    @classmethod
    def dump(cls, obj, fd):
        return json.dump(cls.transmute(obj), fd, cls=cls)
    @classmethod
    def dumps(cls, obj):
        return json.dumps(cls.transmute(obj), cls=cls)
    @classmethod
    def transmute(cls, obj):
        if isinstance(obj, bytes):
            return obj.decode()
        elif isinstance(obj, dict):
            return {
                    cls.transmute(key): cls.transmute(value)
                    for key, value in obj.items()
            }
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, imapclient.response_types.Envelope):
            return {
                    'date': obj.date,
                    'subject': obj.subject,
                    'from': obj.from_,
                    'sender': obj.sender,
                    'reply_to': obj.reply_to,
                    'to': obj.to,
                    'cc': obj.cc,
                    'in_reply_to': obj.in_reply_to,
            }
        elif isinstance(obj, imapclient.response_types.Address):
            return f'{obj.name} <{obj.mailbox}@{obj.host}>'
        else:
            return obj
    def default(self, obj):
        newobj = self.transmute(obj)
        if newobj is obj:
            return super().default(obj)
        else:
            return newobj

class yamf:
    def __init__(self, host, port, ssl, user, pw):
        self.host = host
        self.user = user
        self.imap = imapclient.IMAPClient(host, port, ssl=ssl, use_uid=False)
        print(self.imap.welcome.decode())
        resp = self.imap.login(user, pw)
        print(resp.decode())
        self.imap.normalise_times = False
    def __del__(self):
        resp = self.imap.logout()
        print(resp.decode())
    #def gmail_go(self, query=''):
    #    result = self.imap.gmail_search(query)
    #    print(result)
    #    import pdb; pdb.set_trace()
    def _go_subrange(self, path, msgnums):
        msgs = self.imap.fetch(msgnums, 'UID FLAGS INTERNALDATE RFC822 RFC822.SIZE ENVELOPE'.split(' '))
        try:
            msgslabels = self.imap.get_gmail_labels(msgnums)
            msgs = [{
                **msgs[num], **msglables[num]
            } for num in msgnums]
        except:
            msgs = [msgs[num] for num in msgnums]
        for msg in msgs:
            from_ = msg[b'ENVELOPE'].from_[0]
            fn = os.path.join(path, f"{msg[b'UID']:08}-{msg[b'INTERNALDATE'].isoformat()}-{from_.mailbox.decode()}_{from_.host.decode()}")
            with open(fn, 'wb') as fd:
                fd.write(msg.pop(b'RFC822'))
            with open(fn + '.json', 'w') as fd:
                IMAPJSONEncoder.dump(msg, fd)
            print(fn)
    def go(self, directory='', pattern='*', blocksize=128):
        folders = self.imap.list_folders(directory=directory, pattern=pattern)
        print(folders)
        for flags, delimiter, folder in folders:
            select = self.imap.select_folder(folder, readonly=True)
            path = os.path.join('imap', *folder.split(delimiter.decode()))
            os.makedirs(path, exist_ok=True)
            with open(path + '.json', 'w') as folderjson:
                IMAPJSONEncoder.dump({'folder_flags': flags, **select}, folderjson)
            exists = select[b'EXISTS']
            print(flags, delimiter, folder, select)
            for idx in range(1,exists+1, blocksize):
                msgnums = [*range(idx, min(idx + blocksize, exists))]
                self._go_subrange(path, msgnums)

#class yamf:
#
#    def _call(self, method, *params, expected = 'OK', list = False):
#        result, data = getattr(self.imap, method)(*params)
#        if result != expected:
#            raise Exception(result, *data)
#        if not list:
#            if len(data) > 1:
#                raise Exception(data)
#            data = data[0]
#        return data
#
#    def __init__(self, host, port, ssl, user, pw):
#        IMAP = imaplib.IMAP4_SSL if ssl else imaplib.IMAP4
#        self.imap = IMAP(host, port)
#        print(self.imap.welcome.decode())
#        resp = self._call('login', user, pw)
#        print(resp.decode())
#        self.imap.normalise_times = False
#
#    def __del__(self):
#        resp = self._call('logout', expected='BYE')
#        print(resp.decode())
#
#    def go(self):
#        data = self._call('uid', 'search', None, 'ALL')
#        print(data)

def main():
    client = yamf(cfg.host, cfg.port, cfg.ssl, cfg.user, cfg.pw)
    client.go(pattern=cfg.pattern)
    #client.gmail_go()

if __name__ == '__main__':
    main()

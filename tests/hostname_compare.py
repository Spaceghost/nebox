#!/usr/bin/env python3
"""Side-by-side test of nebox hostname against Debian hostname 3.23+nmu1
(and its dnsdomainname, domainname, ypdomainname, nisdomainname names).
Usage: tests/hostname_compare.py path/to/nebox
Three kinds of case. Plain ones run in the container as they are (as
root, in a private UTS namespace): options, --help, -V, usage errors and
setting names as a user (EPERM). UTS cases run in a private user and UTS
namespace (unshare -ru, or unshare -u as root) where setting the host and
NIS domain names works; the names are set beforehand and printed after
the command with the reference tools. Network cases run in a private user,
mount, network and UTS namespace (unshare -rmnu) with fixture /etc/hosts,
/etc/host.conf, /etc/nsswitch.conf and /etc/resolv.conf bound over the real
ones, dummy interfaces with fixed IPv4/IPv6 addresses, the host name set,
and a small DNS server on 127.0.0.1:53 answering A, AAAA, CNAME and PTR
queries from a fixture table (NXDOMAIN for unknown names, NODATA for
names without the type asked for, no answer for names marked to drop).
-V/--version prints nebox's line and only its status is compared."""
import json, os, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='hostname-compare-', dir='/dev/shm')
os.chmod(d, 0o755)
ROOT = os.geteuid() == 0
NAMES = ['hostname', 'dnsdomainname', 'domainname', 'ypdomainname', 'nisdomainname']
nbin = os.path.join(d, 'nbin')
os.mkdir(nbin)
for n in NAMES:
    os.symlink(NEBOX, os.path.join(nbin, n))
REFPATH = '/usr/bin:/bin:/usr/sbin:/sbin'
NEBPATH = nbin + ':' + REFPATH

DNS = r'''
import json, socket, struct, sys
recs = json.load(open(sys.argv[1]))
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('127.0.0.1', 53))
open(sys.argv[2], 'w').write('ready\n')
TYPES = {'A': 1, 'CNAME': 5, 'PTR': 12, 'TXT': 16, 'AAAA': 28}
def wire(name):
    out = b''
    for label in name.rstrip('.').split('.'):
        if label:
            out += bytes([len(label)]) + label.encode()
    return out + b'\0'
def rdata(t, v):
    if t == 'A':
        return socket.inet_pton(socket.AF_INET, v)
    if t == 'AAAA':
        return socket.inet_pton(socket.AF_INET6, v)
    if t in ('CNAME', 'PTR'):
        return wire(v)
    return bytes([len(v)]) + v.encode()
while True:
    q, peer = s.recvfrom(4096)
    qid, flags, qd = struct.unpack('>HHH', q[:6])
    i = 12
    labels = []
    while q[i]:
        labels.append(q[i + 1:i + 1 + q[i]].decode('latin-1'))
        i += q[i] + 1
    qtype = struct.unpack('>H', q[i + 1:i + 3])[0]
    question = q[12:i + 5]
    name = '.'.join(labels).lower()
    if name in recs.get('drop', []):
        continue
    rcode = 0
    ans = []
    cur = name
    seen = set()
    if cur in recs.get('servfail', []):
        rcode = 2
    elif cur not in recs['names']:
        rcode = 3
    else:
        while cur in recs['names'] and cur not in seen:
            seen.add(cur)
            rr = recs['names'][cur]
            cn = [v for t, v in rr if t == 'CNAME']
            if cn and qtype != 5:
                ans.append((cur, 'CNAME', cn[0]))
                cur = cn[0].lower()
                continue
            for t, v in rr:
                if TYPES[t] == qtype:
                    ans.append((cur, t, v))
            break
    body = b''
    for owner, t, v in ans:
        rd = rdata(t, v)
        body += wire(owner) + struct.pack('>HHIH', TYPES[t], 1, 60, len(rd)) + rd
    hdr = struct.pack('>HHHHHH', qid, 0x8180 | (flags & 0x0100) | rcode, 1, len(ans), 0, 0)
    s.sendto(hdr + question + body, peer)
'''
open(os.path.join(d, 'dns.py'), 'w').write(DNS)

HOSTS_BASIC = '''127.0.0.1	localhost
::1		localhost ip6-localhost ip6-loopback
10.1.2.3 myhost.example.com myhost alias1 alias2
# a comment line
2001:db8::5 myhost.example.com myhost6
192.168.7.9	other.example.org other
10.1.2.4 myhost.example.com second
   10.9.9.9   spaced.example.net spaced   # trailing comment
1.2.3.4
bogus-address name
::ffff:10.0.0.7 mapped4
::1 loopv6only
fe80::1 linklocal
10.1.2.3 MULTI.example.com
10.20.30.40 multi
2001:db8::5 multi.example.com
010.1.1.1 leadingzero
10.7.7.7 nodot
fd00::7 ula.example.net ula
10.1.2.3 x.y.z.example.com deep
'''

DNSREC = {
    'names': {
        'myhost.example.com': [['A', '10.1.2.3'], ['AAAA', '2001:db8::5']],
        'dnshost.example.com': [['A', '10.1.2.3'], ['A', '192.168.7.9'], ['AAAA', 'fd00::7']],
        'v6host.example.com': [['AAAA', '2001:db8::5']],
        'v4host.example.com': [['A', '192.168.7.9']],
        'www.example.com': [['CNAME', 'real.example.org']],
        'real.example.org': [['A', '10.1.2.4'], ['AAAA', '2001:db8::5']],
        'chain.example.com': [['CNAME', 'c2.example.com']],
        'c2.example.com': [['CNAME', 'c3.example.net']],
        'c3.example.net': [['A', '10.9.9.9']],
        'dangle.example.com': [['CNAME', 'nowhere.example.com']],
        'textonly.example.com': [['TXT', 'hello']],
        'unreach.example.com': [['A', '203.0.113.5'], ['A', '10.1.2.4'], ['AAAA', '2001:db8:ffff::1']],
        'abs.example.net': [['A', '10.1.2.3']],
        'bare': [['A', '10.7.7.8']],
        'two.dots.example.com': [['A', '10.1.2.3']],
        'two.dots': [['A', '10.1.2.4']],
        'lo4.example.com': [['A', '127.0.0.1'], ['A', '10.1.2.3'], ['AAAA', '::1']],
        '3.2.1.10.in-addr.arpa': [['PTR', 'myhost.example.com']],
        '4.2.1.10.in-addr.arpa': [['PTR', 'second.example.com']],
        '9.7.168.192.in-addr.arpa': [['CNAME', 'alias.ptr.example']],
        'alias.ptr.example': [['PTR', 'other.example.org']],
        '5.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.arpa': [['PTR', 'myhost6.example.com']],
    },
    'drop': ['slow.example.com'],
    'servfail': [],
}

NET_DUAL = ['ip link set lo up',
            'ip link add d0 type dummy', 'ip addr add 10.1.2.3/24 dev d0', 'ip addr add 10.1.2.4/24 dev d0',
            'ip -6 addr add 2001:db8::5/64 dev d0 nodad', 'ip link set d0 up',
            'ip link add d1 type dummy', 'ip addr add 192.168.7.9/16 dev d1', 'ip -6 addr add fd00::7/8 dev d1 nodad',
            'ip link set d1 up',
            'ip link add d2 type dummy', 'ip addr add 172.16.0.1/24 dev d2']
NET_V4 = ['ip link set lo up',
          'ip link add d0 type dummy', 'ip addr add 10.1.2.3/24 dev d0', 'ip addr add 10.1.2.4/24 dev d0',
          'ip link set d0 up', 'ip link add d1 type dummy', 'ip addr add 192.168.7.9/16 dev d1', 'ip link set d1 up']
NET_LO = ['ip link set lo up']

FIX = {}


def fixture(name, hosts=HOSTS_BASIC, hostconf='multi on\n', nss='hosts: files dns\n',
            resolv='nameserver 127.0.0.1\nsearch example.com\n', net=NET_DUAL, dns=True):
    fd = os.path.join(d, 'fx-' + name)
    os.mkdir(fd)
    for fn, content in (('hosts', hosts), ('host.conf', hostconf), ('nsswitch.conf', nss), ('resolv.conf', resolv)):
        open(os.path.join(fd, fn), 'w').write(content)
    json.dump(DNSREC, open(os.path.join(fd, 'rec.json'), 'w'))
    FIX[name] = (fd, net, dns)


fixture('basic')
fixture('nomulti', hostconf='multi off\n')
fixture('nohostconf', hostconf='')
fixture('v4', net=NET_V4)
fixture('lo', net=NET_LO)
fixture('dnsfirst', nss='hosts: dns files\n')
fixture('filesonly', nss='hosts: files\n')
fixture('dnsonly', nss='hosts: dns\n')
fixture('notfound', nss='hosts: dns [NOTFOUND=return] files\n')
fixture('unknownsvc', nss='hosts: files mdns4_minimal [NOTFOUND=return] dns\n')
fixture('lastunknown', nss='hosts: files dns myhostname\n')
fixture('nonss', nss='passwd: files\n')
fixture('min', hosts='127.0.0.1 localhost\n::1 localhost ip6-localhost\n')
fixture('nsdown', hosts='127.0.0.1 localhost\n', resolv='nameserver 127.0.0.9\nsearch example.com\n', dns=False)
fixture('noresolv', hosts='127.0.0.1 localhost\n', resolv='', dns=True)
fixture('domain', hosts='127.0.0.1 localhost\n', resolv='nameserver 127.0.0.1\ndomain example.com\n')
fixture('nosearch', hosts='127.0.0.1 localhost\n', resolv='nameserver 127.0.0.1\n')
fixture('ndots2', hosts='127.0.0.1 localhost\n', resolv='nameserver 127.0.0.1\nsearch example.com\noptions ndots:2\n')
fixture('noaaaa', hosts='127.0.0.1 localhost\n', resolv='nameserver 127.0.0.1\nsearch example.com\noptions no-aaaa\n')
fixture('notld', hosts='127.0.0.1 localhost\n', resolv='nameserver 127.0.0.1\nsearch example.com\noptions no-tld-query\n')
fixture('multisearch', hosts='127.0.0.1 localhost\n',
        resolv='# comment\n; other comment\nnameserver 127.0.0.1\nsearch nope.test example.com example.org\n')
fixture('twons', hosts='127.0.0.1 localhost\n', resolv='nameserver 127.0.0.9\nnameserver 127.0.0.1\nsearch example.com\n')
fixture('slow', hosts='127.0.0.1 localhost\n',
        resolv='nameserver 127.0.0.1\nsearch example.com\noptions timeout:1 attempts:1\n')
fixture('emptyhosts', hosts='')
fixture('weird', hosts='127.0.0.1 localhost\n10.1.2.3\tTab.Example.COM\ttab\n10.1.2.3 dup dup\n'
        '10.1.2.4 dup\n2001:db8::5 dup\n\n   \n#\n10.1.2.3 a#b c\n10.1.2.3 \x00nul\n10.1.2.4 long' + 'x' * 300 + '\n')

CASES = []
# plain: options and errors
for a in ['', '-s', '--short', '-y', '--yp', '--nis', '-b', '-V', '--version', '-h', '--help', '-?', '-x', '-v',
          '--bogus', '--he', '--al', '--a', '-F', '--file', '-sh', '-hs', '-Vh', '-yV', 'a b', '-s a b',
          '-F /nonexistent', '-b -F /nonexistent', '-F /nonexistent name', '-f name', '-d name', '-a name',
          '-i name', '-I name', '-A name', '-s name', '-F /etc/hostname x', '-- -s', '-y -- a b']:
    CASES.append(('plain', None, None, '@ ' + a))
for prog in ['dnsdomainname', 'domainname', 'ypdomainname', 'nisdomainname']:
    for a in ['', '-h', '-V', '-s', '-x', 'a b']:
        CASES.append(('plain', None, None, prog + ' ' + a))
NOVERSION = {'@ -V', '@ --version', '@ -Vh', '@ -yV', 'dnsdomainname -V', 'domainname -V', 'ypdomainname -V',
             'nisdomainname -V'}

# files for -F
FILES = {'f_simple': 'newname\n', 'f_comments': '# first\n\n#x\nfromfile.example.org\nignored\n',
         'f_onlycomments': '#a\n#b\n', 'f_blanks': '\n\n\n', 'f_empty': '', 'f_spaces': '   padded.name   \n',
         'f_nonl': 'nonewline', 'f_invalid': 'bad_name\n', 'f_dash': '-lead\n', 'f_dotdash': 'a.-b\n',
         'f_dots': 'a..b\n', 'f_long': 'x' * 80 + '\n', 'f_64': 'y' * 64 + '\n', 'f_65': 'z' * 65 + '\n',
         'f_nul': 'ab\x00cd\n', 'f_nulfirst': '\x00x\n', 'f_crlf': 'crlf.name\r\n', 'f_tab': '\tTAB\t\n',
         'f_hash_after': 'name#comment\n', 'f_none': '(none)\n', 'f_spaceonly': '   \n', 'f_lastcomment': 'x\n#y\n',
         'f_blankfirst': '\nsecond.line\n', 'f_binary': '\xff\xfe\n', 'f_digits': '12345\n',
         'f_dom': 'nis.example\n'}
fdir = os.path.join(d, 'files')
os.mkdir(fdir)
for k, v in FILES.items():
    open(os.path.join(fdir, k), 'w', encoding='latin-1').write(v)
os.mkdir(os.path.join(fdir, 'f_dir'))
if not ROOT:
    open(os.path.join(fdir, 'f_noperm'), 'w').write('x\n')
    os.chmod(os.path.join(fdir, 'f_noperm'), 0)
FN = sorted(FILES) + ['f_dir', 'f_missing'] + ([] if ROOT else ['f_noperm'])
for f in FN:
    p = os.path.join(fdir, f)
    CASES.append(('plain', None, None, '@ -F ' + p))
    for a in ['-F', '-b -F', '-y -F', '--boot --file']:
        CASES.append(('uts', None, None, '@ %s %s' % (a, p)))
for a in ['newname', 'a.b.c', 'A-b.C-d', '1', '1.2.3.4', 'x' * 63, 'x' * 64, 'x' * 65, "'  spaced  '", "' '", "''",
          '-- -bad', 'bad-', 'a.-b', 'a-.b', 'a..b', 'a_b', '.a', 'a.', 'é', "'tab\there'", "$'x\\ny'", 'UPPER',
          '0', '-b newname', '-b ""', '-y nisname', '-y ""', '-y "with space"', '--nis ' + 'n' * 70, '-y ' + 'n' * 64,
          '-y ' + 'n' * 65, '-b', '-s', '-y', '-f', 'name extra', '-F /dev/null', '-b -F /dev/null',
          '-F /proc/self/status', '-b -F /nonexistent', '-b -F /nonexistent extra', '-f newname', '-d newname']:
    CASES.append(('uts', None, None, '@ ' + a))
for prog in ['domainname', 'ypdomainname', 'nisdomainname', 'dnsdomainname']:
    for a in ['', 'newdom', '""', '-F ' + os.path.join(fdir, 'f_dom'), '-b', '-s', '-b -F /nonexistent']:
        CASES.append(('uts', None, None, prog + ' ' + a))

# network cases: fixture, host name to set, command
SHOW = ['', '-s', '-f', '-d', '-a', '-i', '-I', '-A', '--long', '--domain', '--alias', '--ip-address',
        '--all-ip-addresses', '--all-fqdns', '-f -s', '-s -f', '-i -d']
HOSTS = ['myhost', 'myhost.example.com', 'MYHOST', 'other', 'spaced', 'myhost6', 'mapped4', 'loopv6only',
         'linklocal', 'localhost', 'multi', 'multi.example.com', 'leadingzero', 'nodot', 'ula', 'deep', 'alias1',
         'unknownname', 'dnshost', 'dnshost.example.com', 'v6host', 'v4host', 'www', 'chain', 'dangle', 'textonly',
         'unreach', 'abs.example.net', 'bare', 'two.dots', 'lo4', '10.1.2.3', '123', '1.2', '0x7f.1', '1.2.3.4.5',
         '255.255.255.255', '1.2.3.400', 'x1.2', '08.1.1.1']
for h in HOSTS:
    for s in SHOW:
        CASES.append(('net', 'basic', h, '@ ' + s))
for fx in ['nomulti', 'nohostconf', 'v4', 'lo', 'dnsfirst', 'filesonly', 'dnsonly', 'notfound', 'unknownsvc',
           'lastunknown', 'nonss', 'min', 'emptyhosts', 'weird']:
    for h in ['myhost', 'myhost.example.com', 'multi', 'other', 'dnshost', 'unknownname', 'www', 'unreach', 'lo4',
              'tab.example.com', 'dup', 'c', 'nul', 'long' + 'x' * 50]:
        for s in ['', '-f', '-d', '-a', '-i', '-I', '-A']:
            CASES.append(('net', fx, h, '@ ' + s))
for fx in ['nsdown', 'noresolv', 'domain', 'nosearch', 'ndots2', 'noaaaa', 'notld', 'multisearch', 'twons']:
    for h in ['myhost', 'myhost.example.com', 'dnshost', 'two.dots', 'bare', 'www', 'chain', 'textonly',
              'unknownname', 'v6host', 'localhost', 'abs.example.net']:
        for s in ['-f', '-d', '-a', '-i', '-A']:
            CASES.append(('net', fx, h, '@ ' + s))
for s in ['-f', '-a', '-i']:
    CASES.append(('net', 'slow', 'slow', '@ ' + s))
for prog in ['dnsdomainname', 'domainname', 'ypdomainname', 'nisdomainname']:
    for h in ['myhost', 'myhost.example.com', 'unknownname', 'chain']:
        for a in ['', '-f', '-s', '-y', '-a']:
            CASES.append(('net', 'basic', h, prog + ' ' + a))


def run(c, which):
    kind, fx, host, cmd = c
    env = dict(os.environ, LC_ALL='C', PATH=REFPATH if which == 'ref' else NEBPATH)
    sh = cmd.replace('@', 'hostname', 1) if cmd.startswith('@') else cmd
    if kind == 'plain':
        argv = (['unshare', '-u'] if ROOT else []) + ['sh', '-c', sh]
    elif kind == 'uts':
        script = ('/bin/hostname start.example.org && /bin/domainname startdom && { %s; }; echo "rc=$?"; '
                  '/bin/hostname; /bin/domainname' % sh)
        argv = (['unshare', '-u'] if ROOT else ['unshare', '-ru']) + ['sh', '-c', script]
    else:
        fd, net, dns = FIX[fx]
        parts = list(net)
        for fn in ('hosts', 'host.conf', 'nsswitch.conf', 'resolv.conf'):
            parts.append('mount --bind %s/%s /etc/%s' % (fd, fn, fn))
        parts.append('/bin/hostname %s' % host)
        if dns:
            parts.append('mkfifo $T/fifo && { python3 -I %s/dns.py %s/rec.json $T/fifo & } && read x < $T/fifo' % (d, fd))
        script = '{ %s; } >/dev/null 2>&1 || echo SETUP FAILED; %s; echo "rc=$?"' % (' && '.join(parts), sh)
        tdir = tempfile.mkdtemp(dir=d)
        env['T'] = tdir
        argv = (['unshare', '-mnup'] if ROOT else ['unshare', '-rmnup']) + ['-f', '--kill-child', 'sh', '-c', script]
    p = subprocess.run(argv, cwd=d, env=env, capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout, p.stderr


def check(c):
    r = run(c, 'ref')
    n = run(c, 'nebox')
    if c[3] in NOVERSION:
        r, n = (r[0], r[1].split(b'\n', 1)[-1], r[2]), (n[0], n[1].split(b'\n', 1)[-1], n[2])
    return c, r, n


bad = 0
setup_failed = 0
with ThreadPoolExecutor(8) as ex:
    for c, r, n in ex.map(check, CASES):
        if b'SETUP FAILED' in r[1]:
            setup_failed += 1
        if r != n:
            bad += 1
            if bad <= 30:
                print('MISMATCH:', c)
                for name, x, y in zip(('status', 'stdout', 'stderr'), r, n):
                    if x != y:
                        print('  %s ref:   %r' % (name, x if isinstance(x, int) else x[:400]))
                        print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:400]))
print('hostname_compare: %d cases%s, %d mismatches%s' % (len(CASES), ' (as root)' if ROOT else '', bad,
      ', %d setup failures' % setup_failed if setup_failed else ''))
shutil.rmtree(d)
sys.exit(1 if bad or setup_failed else 0)

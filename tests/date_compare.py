#!/usr/bin/env python3
"""Side-by-side test of nebox date against GNU coreutils 9.1 date.
Usage: tests/date_compare.py path/to/nebox [random-cases] [seed]
Fixed cases: every option and long option (-d -f -I[FMT] --rfc-3339 -R -r
--resolution -s -u --debug, the MMDDhhmm[[CC]YY][.ss] operand, %-N), their
errors (argmatch, multiple formats, mutually exclusive options, extra
operands, a missing leading '+', getopt errors), -f from files, standard
input, directories and missing files, /dev/full; then parse-datetime's
grammar: absolute dates in every form, times with am/pm, decimal seconds,
zones (named, military, numeric, DST, local abbreviations), the TZ="..."
prefix, ordinals and day names, relative items with ago/hence and
this/next/last, @N, ISO 8601 'T', comments, invalid strings and overflow,
each under several TZ values and many with --debug. Then random strings
built from grammar pieces. stdout, stderr and exit status must match. A
case whose result depends on the current time is rerun when it differs;
when GNU's own two runs differ, the nanoseconds of the clock are not
compared. -s cases are skipped when run as root."""
import os, random, re, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 11
GNU = '/usr/bin/date'
d = tempfile.mkdtemp(prefix='date-compare-', dir='/dev/shm')
for name, target in (('gnu', GNU), ('nb', NEBOX)):
    os.mkdir(os.path.join(d, name))
    os.symlink(target, os.path.join(d, name, 'date'))
open(os.path.join(d, 'dates'), 'w').write(
    '2020-01-01\n2020-02-30\n\n  1999-12-31 23:59:59 UTC\nbogus line\n@0\nTZ="Asia/Tokyo" 2021-06-01 12:00\nlast line no newline')
open(os.path.join(d, 'nul'), 'wb').write(b'2020-01-01\x00junk\nfoo\x00bar\n2021-01-01\n')
open(os.path.join(d, 'empty'), 'w').write('')
os.mkdir(os.path.join(d, 'dir'))
open(os.path.join(d, 'ref'), 'w').write('x')
os.utime(os.path.join(d, 'ref'), ns=(1700000000123456789, 1700000000123456789))
ROOT = os.geteuid() == 0
rnd = random.Random(SEED)

TZS = ['UTC0', 'America/New_York', 'Asia/Tokyo', 'Australia/Lord_Howe', 'Europe/Helsinki',
       'EST5EDT,M3.2.0,M11.1.0', '<+0530>-5:30', 'NZST-12NZDT,M9.5.0,M4.1.0/3', None]


def sq(s):
    return "'" + s.replace("'", "'\\''") + "'"


CASES = []   # (tz, shell command, flags)


def C(cmd, tz='America/New_York', now=False):
    CASES.append((tz, cmd, now))


# options and their errors
for o in ['', '-u', '--utc', '--uct', '--universal', '-R', '--rfc-email', '--rfc-822', '--rfc-2822', '--rfc',
          '-I', '-Id', '-Ih', '-Im', '-Is', '-In', '-Ihours', '-Iminutes', '-Iseconds', '-Ins', '-Idate',
          '--iso-8601', '--iso-8601=hours', '--iso-8601=m', '--iso=s', '--iso-8601=n', '--iso-8601=', '-Ix',
          '--iso-8601=x', '--rfc-3339=date', '--rfc-3339=seconds', '--rfc-3339=ns', '--rfc-3339=s',
          '--rfc-3339=d', '--rfc-3339=n', '--rfc-3339=', '--rfc-3339=hours', '--rfc-3339', '--rfc-3', '-R -I',
          '-I -I', '-Is --rfc-3339=ns', '-R +%F', '-I +%F', '--iso-8601=hours +%T']:
    C('date %s -d %s' % (o, sq('2024-03-10 01:59:58.123456789')))
    C('date %s -d %s' % (o, sq('2024-07-04 12:34:56.5 +0530')), tz='Australia/Lord_Howe')
for o in ['-x', '--bogus', '--d', '--da=2020-01-01', '--date', '-d', '-f', '-r', '--reference', '-s', '--set',
          '--debug=1', '--utc=1', '--help=x', '-uIs -d @0', '--res', '--resolution', '--resolution +%s',
          '--resolution -d @0', '--resolution -r ref', '-d @0 -f dates', '-d @0 -r ref', '-r ref -f dates',
          '-s @0 -d @0', '-s @0 -r ref', '-s @0 -f dates', '--set=@0 --resolution',
          '-d @0 extra', '-d @0 +%F +%T', '+%F +%T', '1 2', '0101000020 3', '-d @0 0101000020',
          '-d @0 +%F', '-r ref', '-r ref +%F.%N', '-r nonexistent', '--reference=ref -u', '-r dir +%s',
          '-f dates', '-f dates -u +%F%t%T', '-f dates --debug +%s', '--file=dates -R', '-f nul', '-f empty',
          '-f dir', '-f nonexistent', '-f -', '-f - < dates', '-f - +%s < nul', '--debug -f - < /dev/null',
          '-d @0 +%-N', '-d @1.5 +%-N%%-N%-3N%%%-N', '--resolution +%-N', '-d @0 +', '-d @0 +%',
          '-d @0 "+%s %c %x %X %r %p"', '-d @99999999999999999', '-d @-99999999999999999 +%s',
          '-d @67768036191676799 +%F', '-f dates > /dev/full', '-d @0 > /dev/full',
          '--version > /dev/full', '--help > /dev/full', '-d', '-d ""', '-d " "', '--date=', '--debug -d ""',
          '--debug', '--debug -u -d @0', '--debug -R -d "2020-01-01 10:00"', '--debug -r ref',
          '--debug --resolution', '--debug -Ins -d "TZ=\\"Asia/Tokyo\\" 2020-06-01 10:00"',
          '-d now -d @5', '-d @5 -d @6 +%s', '-u -d "2020-01-01 10:00" -u']:
    C('date %s' % o)
    C('date %s' % o, tz='UTC0')
C('date --help | head -n 93')
C('date -u --help | head -n 3')
C('date --version | head -n 1 | cut -c1-5')
C('date --version >/dev/null; echo $?')
C('date --help >/dev/null; echo $?')
for z in TZS:
    C('date -d @0', tz=z)
    C('date -d @1700000000.987654321 "+%c|%x|%X|%Z|%z|%:z|%::z|%:::z|%N"', tz=z)
    C('date -u -d @1700000000 "+%c|%Z|%z"', tz=z)
    C('date -R -d @1700000000', tz=z)
    C('date -Ins -d @1700000000.5', tz=z)
    C('date --rfc-3339=ns -d @1700000000.5', tz=z)
    C('date -f dates', tz=z)
    C('date --debug -f dates', tz=z)
# setting the clock (an unprivileged user gets EPERM and the date still prints)
if not ROOT:
    for o in ['-s @0', '--set=2020-01-01', '-s "2020-02-30"', '-u -s @1', '-s @0 +%s', '--debug -s @0',
              '0101000020', '010100002020', '0101000020.30', '01010000', '010100001970.59', '0101000020.60',
              '13010000', '0230000020', '0101000020.3', '0101000020.', 'x101000020', '0101000020 +%s',
              '-u 0101000020', '"" ', '010100002020.30.1']:
        C('date %s' % o)
        C('date %s' % o, tz='Asia/Tokyo')

# parse-datetime's grammar, against fixed dates
FMT = '+%F %T.%N %z %Z'
GRAMMAR = [
    # @N
    '@0', '@1', '@-1', '@+5', '@1.5', '@-1.5', '@-0.0000000001', '@1.1234567891', '@1,5', '@ 5', '@- 5',
    '@9223372036854775807', '@-9223372036854775808', '@9223372036854775808', '@', '@x', '@5 x', '@5 sec',
    '@1.5 sec', ' @5', '@5 ', '@5 (c)', 'x @5', '@@5', '@-',
    # ISO 8601 and other absolute dates
    '2020-01-01', '2020-1-1', '2020-02-29', '2021-02-29', '2020-13-01', '2020-00-10', '2020-01-00',
    '2020-01-32', '2020-12-31', '1970-01-01', '1969-12-31', '0000-01-01', '0001-01-01', '-0001-01-01',
    '9999-12-31', '10000-01-01', '99999-01-01', '2147485547-01-01', '2147485548-01-01', '-2147481748-01-01',
    '20-01-01', '69-01-01', '68-12-31', '99-12-31', '00-01-01', '020-01-01', '2020-01-+5', '17-+5-2',
    '2020--01--01', '2020-01-01-', '2020-01', '2020 - 01 - 01', '2020-01-01T', '2020-01-01 T',
    '1/2', '01/02/03', '1/2/2003', '12/31/99', '12/31/1999', '2003/01/02', '0003/01/02', '1/2/3/4', '13/1',
    '1/32', '2/29/2001', '2/29/2000', '1/', '/1', '1//2',
    '17 jun 1992', '17 june 1992', '17-jun-1992', '17-JUN-92', 'jun-17-1992', 'JUN-17-92', 'jun 17',
    'jun 17 1992', 'jun 17, 1992', 'june 17, 92', '17 jun', 'sep 9', 'sept 9', 'sept. 9', 'sep. 9', 'SEPT 9',
    'september 9', 'septem 9', 'jan', 'jan,', 'jan 1,', 'jan 1, x', 'jan -1', 'jan -1 -2', 'jan -1 2', '1 jan -2',
    'jan.', 'jan. 5', 'Jan.1', 'january 5 2020', 'fe 2', 'feb 30', 'feb 29 2020', 'feb 29 2021', 'may 5',
    'decem 5', 'dec 31 1969 23:59:59 utc', '1 jan 10:00', '1 jan 2020 10:00', 'jan 1 2020 10:00',
    '20200101', '200101', '2020010', '1999123', '19991231235959', '20201301', '20200230', '0101', '000101',
    '1999', '99', '9', '123', '12345', '123456', '1234567', '123456789012',
    # times
    '10:00', '10:00:00', '10:00:59.5', '10:00:60', '10:00:61', '23:59:59.999999999', '24:00', '00:00',
    '0:0', '1:2:3', '10:60', '10:00:00.1234567891', '10:00:00,5', '10:00:00.', '10:00:', '10:', ':00',
    '10:00:00:00', '1 pm', '1pm', '12am', '12pm', '12 a.m.', '12 P.M.', '0am', '13pm', '11:59 pm',
    '11:59:59 am', '12:00:00.5 pm', '10:00 am pm', '10 am 11 pm', 'am', 'pm', '10:00am utc', '10:00 pm EST',
    '1000', '1230', '2359', '2400', '0060', '10 00', '100', '1', '10:00 10:00', '1:00 2:00',
    '2020-01-01 10:00', '2020-01-01T10:00', '2020-01-01T10', '2020-01-01T10Z', '2020-01-01T10:00:00Z',
    '2020-01-01T10:00:00.5Z', '2020-01-01T10:00:00,5+01:00', '2020-01-01T10:00+0530', '2020-01-01T10+05',
    '2020-01-01T10:00:00-23:59', '2020-01-01T10:00:00+24:00', '2020-01-01T10:00:00+24:01',
    '2020-01-01T10:00:00+2401', '2020-01-01T10:00:00+999', '2020-01-01T10:00:00+1', '2020-01-01T10:00 pm',
    '2020-01-01T10:00:00 +5 hours', '2020-01-01t10:00', '2020-01-01 t 10:00', '2020-01-01T', '2020-01-01Tx',
    '2020-01-01T10:', '2020-01-01T:10', '2020-01-01T10 pm',
    # zones
    '2020-01-01 10:00 UTC', '2020-01-01 10:00 utc', '2020-01-01 10:00 GMT', '2020-01-01 10:00 UT',
    '2020-01-01 10:00 Z', '2020-01-01 10:00 z', '2020-01-01 10:00 EST', '2020-01-01 10:00 EDT',
    '2020-07-01 10:00 EDT', '2020-01-01 10:00 PST', '2020-01-01 10:00 JST', '2020-01-01 10:00 IST',
    '2020-01-01 10:00 NST', '2020-01-01 10:00 NDT', '2020-01-01 10:00 CEST', '2020-01-01 10:00 MESZ',
    '2020-01-01 10:00 BST', '2020-01-01 10:00 WET', '2020-01-01 10:00 EST DST', '2020-01-01 10:00 UTC DST',
    '2020-01-01 10:00 DST', '2020-01-01 10:00 E.S.T.', '2020-01-01 10:00 U.T.C.', '2020-01-01 10:00 e.d.t',
    '2020-01-01 10:00 A', '2020-01-01 10:00 M', '2020-01-01 10:00 N', '2020-01-01 10:00 Y', '2020-01-01 10:00 J',
    '2020-01-01 10:00 T', '2020-01-01 T', 'T', 'T +1 hour', 'T -1 day', 'T 5', 'A', 'Z', 'UTC', 'J',
    '2020-01-01 10:00 +05', '2020-01-01 10:00 -0530', '2020-01-01 10:00 +5:30', '2020-01-01 10:00 +05:30',
    '2020-01-01 10:00 -5:3', '2020-01-01 10:00 +24', '2020-01-01 10:00 +2400', '2020-01-01 10:00 +2401',
    '2020-01-01 10:00 +123', '2020-01-01 10:00 +12345', '2020-01-01 10:00 -00', '2020-01-01 10:00 UTC+3',
    '2020-01-01 10:00 UTC-0330', '2020-01-01 10:00 UTC+3:30', '2020-01-01 10:00 EST+1', '2020-01-01 10:00 UTC+25',
    '2020-01-01 10:00 UTC +1 hour', '2020-01-01 10:00 UTC -1 day', '2020-01-01 10:00 UTC+1:', '10:00 +1 hour',
    '10:00 -1 day', '10:00+01', '10:00-01:30', '10:00:00+0100', '10:00:00.5-0100', '10:00 UTC EST',
    '10:00 +01 +02', '2020-01-01 10:00 EST EDT', '2020-01-01 10:00 +01 UTC', '1 +2', '1 -0130', '1 +2 days',
    '1 +2:30', '2020-01-01 +0100', '2020-01-01 10:00 +01:', '2020-01-01 10:00 +01:x',
    # local zone abbreviations (tLOCAL_ZONE) for the TZ in effect
    '2020-01-01 10:00 EST', '2020-07-01 10:00 EST', '2020-07-01 10:00 EDT DST', '2020-01-01 10:00 JST',
    '2020-06-30 EEST', '2020-01-01 EET', '2020-06-30 EEST DST', '2020-01-01 10:00 LHDT', '2020-01-01 10:00 NZDT',
    '2020-07-01 10:00 NZST', '2020-03-08 02:30 EDT', '2020-03-08 02:30 EST', '2020-11-01 01:30 EDT',
    '2020-11-01 01:30 EST',
    # TZ="..." prefix
    'TZ="Asia/Tokyo" 2020-01-01 10:00', 'TZ="UTC0" 2020-06-01', 'TZ="America/New_York" 2020-03-08 02:30',
    'TZ="EST5EDT" 2020-07-01 12:00', ' TZ="Asia/Tokyo"  10:00', 'TZ="Asia/Tokyo"', 'TZ=""', 'TZ="" 10:00',
    'TZ="A\\"B" 10:00', 'TZ="A\\\\B" 10:00', 'TZ="A\\B" 10:00', 'TZ="Asia/Tokyo 10:00', 'TZ=Asia/Tokyo 10:00',
    'tz="Asia/Tokyo" 10:00', 'TZ="Foo/Bar" 2020-01-01', 'TZ="<+0530>-5:30" 2020-01-01 10:00 IST',
    'TZ="Europe/Helsinki" 2016-06-30 EEST', 'TZ="Asia/Tokyo" 2016-06-30 EEST', 'TZ="Asia/Tokyo" @0',
    'TZ="Asia/Tokyo" 2020-01-01 TZ="UTC0"', 'TZ="Australia/Lord_Howe" 2020-10-04 02:15',
    'TZ="Australia/Lord_Howe" 2020-04-05 01:45', 'TZ="Asia/Tokyo" 2020-01-01 10:00 +1 day',
    # day names and ordinals
    '2020-01-01 monday', '2020-01-01 mon', 'monday', 'mon', 'MON', 'Mon.', 'tues', 'tue', 'wed', 'wednes',
    'wednesday', 'thu', 'thur', 'thurs', 'thursday', 'fri', 'sat', 'sun', 'sunday,', 'sun ,', 'sun,,',
    'next fri', 'last fri', 'this fri', 'first fri', 'second fri', 'third fri', 'fourth sat', 'twelfth sun',
    'eighth mon', 'eleventh tue', 'next', 'last', 'this', 'next x', '0 fri', '1 fri', '2 fri', '12 fri',
    '13 fri', '100 fri', '-1 fri', '+1 fri', 'fri 10:00', 'fri 2020-01-01', '2020-01-01 fri 10:00',
    'fri sat', 'fri next fri', 'next fri 10:00 +1 day', 'last sun 1 month ago', 'next fri utc',
    '10:00 next mon', 'mon 1 week', '99999999999999 fri', '922337203685477580 fri', 'friday 12:00 EDT',
    # relative items
    '1 year', '1 years', '+1 year', '-1 year', '1 year ago', '1 year hence', 'year', 'years', 'next year',
    'last year', 'this year', '2 months', 'month', 'next month', '1 fortnight', 'fortnight', '2 fortnights ago',
    '1 week', '3 weeks', 'week', 'last week', '1 day', 'day', 'days', '2 days ago', 'next day', 'last day',
    'this day', 'tomorrow', 'yesterday', 'today', 'now', 'today now', 'now now', '1 hour', 'hour', '2 hours ago',
    '90 minutes', '1 min', 'min', 'mins', '5 mins ago', '30 seconds', 'second', 'sec', 'secs', '1.5 seconds',
    '1.5 sec ago', '-1.5 sec', '+1.5 sec', '1,5 sec', '-0.000000001 sec', '1.0000000001 sec',
    '-1.0000000001 sec', '1.5 min', '1.5', '-1.5', '1 ago', 'ago', 'hence', '2 days 3 hours ago',
    '1 day ago ago', '1 day 1 day', 'next next day', 'third day', 'first day', 'second', 'twelfth month',
    '2020-01-01 +1 day', '2020-01-01 + 1 day', '2020-01-01 -1 day', '2020-01-01 - 1 day', '2020-01-31 +1 month',
    '2020-01-31 1 month ago', '2020-02-29 +1 year', '2020-02-29 +4 years', '2020-03-31 -1 month',
    '2020-01-01 +2 weeks', '2020-01-01 10:00 +36 hours', '2020-01-01 10:00 -90 minutes',
    '2020-01-01 10:00 +3600 seconds', '2020-03-07 12:00 +1 day', '2020-03-07 12:00 +24 hours',
    '2020-03-08 01:30 +1 hour', '2020-03-08 03:30 -1 hour', '2020-11-01 00:30 +1 hour', '2020-11-01 00:30 +2 hours',
    '2020-03-08 02:30 1 day ago', '2020-01-01 10:00:00.5 +0.6 sec', '2020-01-01 10:00:00.5 -0.6 sec',
    '20200101 +2 days', '20200101 2 days', '20200101 -2 days', '1200 +2 days', '12 +2 hours', '2020 +1 year',
    '2020-01-01 2020', '2020-01-01 10:00 2021', '2020-01-01 21', '2020-01-01 +1 day 2021', 'jan 1 10:00 2021',
    '10:00 jan 1 2021', '10:00 2021', '2021 10:00', 'jan 1 21', 'jan 1 2021 2022',
    '2020-01-01 9223372036854775807 sec', '2020-01-01 9223372036854775807 hours', '2020-01-01 -9223372036854775808 sec',
    '2020-01-01 2147483647 years', '2020-01-01 2147483648 months', '2020-01-01 2147483647 days',
    '2020-01-01 1317624576693539401 weeks', '9223372036854775807 seconds', '922337203685477581 fortnight',
    '9223372036854775807 sec 1 sec', '2020-01-01 1000000000 years', '2020-01-01 -2000000000 years',
    '2020-01-01 100000000 days', '-9223372036854775808 sec -1 sec',
    # comments and junk
    '(comment) 2020-01-01', '2020-01-01 (comment)', '2020-(x)01-01', '((nested) x) 2020-01-01',
    '2020-01-01 (unterminated', ')', '(', '()', 'x', 'xyz', '2020-01-01 xyz', 'xyz 2020-01-01',
    'abcdefghijklmnopqrstuvwxyz', 'januaryfebruarymarch 1', '2020-01-01 10:00 ?', '2020-01-01, 10:00',
    '2020-01-01;', '2020-01-01 10:00:00 . 5', '#', '2020-01-01\t10:00', '\n2020-01-01\n', ' ', '', '0',
    '-', '+', '- 5', '+ 5 days', '-x', '5-', '5 :', '5:', '2020-01-01 10:00 + ', 'tomorrowx', 'a.m.',
    '1 a.m', '1 a.m.x', 'p.m.', 'utc.', '.', '..', 'jan..1', 'sec.', 'DST', 'EST DST', 'EDT DST', 'dst',
    # overflow in the lexer and the grammar
    '9223372036854775807', '9223372036854775808', '-9223372036854775808 sec', '-9223372036854775809 sec',
    '99999999999999999999 days', '2020-01-01 10:00 +99999999999999999999', '9223372036854775807:00',
    '10:9223372036854775807', '10:4294967296', '4294967306:00', '10:00:4294967296', '2020-4294967297-01',
    '2020-01-4294967297', '2147483648-01-01', '-2147483649-01-01', 'jan -9223372036854775808 -1',
    '1 jan -9223372036854775808', '2020--9223372036854775808-01', 'UTC+9223372036854775807',
    'UTC+153722867280912930', '9223372036854775807 fri', '1.99999999999999999999 sec',
    '-9223372036854775808.5 sec', '9223372036854775807.5 sec',
]
for s in GRAMMAR:
    C('date -d %s %s' % (sq(s), sq(FMT)), now=True)
    C('date --debug -d %s %s' % (sq(s), sq(FMT)), now=True)
for z in ['UTC0', 'Asia/Tokyo', 'Australia/Lord_Howe', 'Europe/Helsinki', 'NZST-12NZDT,M9.5.0,M4.1.0/3',
          '<+0530>-5:30', None]:
    for s in GRAMMAR[::3]:
        C('date -d %s %s' % (sq(s), sq(FMT)), tz=z, now=True)
    for s in GRAMMAR[1::7]:
        C('date --debug -d %s %s' % (sq(s), sq(FMT)), tz=z, now=True)
# DST edges in New York and Lord Howe
for s in ['2024-03-10 01:59:59', '2024-03-10 02:00', '2024-03-10 02:30', '2024-03-10 03:00', '2024-11-03 00:59',
          '2024-11-03 01:00', '2024-11-03 01:30', '2024-11-03 01:59:59', '2024-11-03 02:00', '2024-11-03 01:30 EDT',
          '2024-11-03 01:30 EST', '2024-11-03 01:30 EDT +1 hour', '2024-11-03 01:30 EST -1 hour',
          '2024-03-10 02:30 EST', '2024-03-10 02:30 EDT', '2024-03-09 02:30 +1 day', '2024-03-10 02:30 -1 day',
          '2024-11-02 01:30 +1 day', '2024-11-03 01:30 1 day ago', '2024-03-10 12:00 -1 day', '2024-03-10 -1 day',
          '2024-11-03 +12 hours', '2024-07-01 12:00 EST', '2024-01-01 12:00 EDT', '2024-01-01 12:00 EDT DST',
          '2024-01-01 12:00 EST DST']:
    for z in ['America/New_York', 'EST5EDT,M3.2.0,M11.1.0']:
        C('date -d %s %s' % (sq(s), sq(FMT)), tz=z)
        C('date --debug -d %s %s' % (sq(s), sq(FMT)), tz=z)
for s in ['2024-04-07 01:30', '2024-04-07 01:45', '2024-04-07 02:00', '2024-10-06 02:00', '2024-10-06 02:15',
          '2024-10-06 02:30', '2024-10-06 02:29:59', '2024-04-07 01:45 LHDT', '2024-04-07 01:45 LHST',
          '2024-10-06 02:15 +1 day', '2024-04-06 01:45 +1 day', '2024-10-05 02:15 +1 day', '2024-01-01 12:00 LHST']:
    C('date -d %s %s' % (sq(s), sq(FMT)), tz='Australia/Lord_Howe')
    C('date --debug -d %s %s' % (sq(s), sq(FMT)), tz='Australia/Lord_Howe')
# historical offsets, far years and the time_t edges
for s in ['1900-01-01', '1883-11-18 12:00', '1883-11-18 11:59:59 +1 sec', '1800-06-01 10:00 UTC', '0099-01-01',
          '-100-01-01', '1000000-01-01', '2147483647-12-31 23:59:59', '2147485547-12-31 23:59:59 UTC',
          '292277026596-12-04 15:30:07 UTC', '-292277022657-01-27 08:29:52 UTC',
          '1969-12-31 23:00:00 -0100', '@-62135596800', '@253402300799', '1970-01-01 00:00 +1 sec ago']:
    C('date -d %s %s' % (sq(s), sq('+%Y|%F %T %z %Z|%s')), tz='America/New_York')
    C('date --debug -d %s %s' % (sq(s), sq('+%Y|%s')), tz='Asia/Kolkata')

# random strings from grammar pieces
MONS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec', 'january',
        'february', 'march', 'september', 'December', 'JUNE', 'jan.']
DAYS = ['mon', 'tue', 'tues', 'wed', 'wednes', 'thu', 'thur', 'thurs', 'fri', 'sat', 'sun', 'monday', 'Friday',
        'SATURDAY', 'sun,']
UNITS = ['year', 'years', 'month', 'months', 'fortnight', 'fortnights', 'week', 'weeks', 'day', 'days', 'hour',
         'hours', 'minute', 'minutes', 'min', 'mins', 'second', 'seconds', 'sec', 'secs']
ZONES = ['UTC', 'GMT', 'UT', 'Z', 'EST', 'EDT', 'CST', 'PDT', 'JST', 'IST', 'NZDT', 'CEST', 'BST', 'EET', 'EEST',
         'A', 'M', 'N', 'Y', 'EST DST', 'UTC DST', 'LHDT', 'LHST', 'NZST', 'utc', 'e.s.t.']


def r_year():
    return rnd.choice(['%04d' % rnd.randint(1900, 2100), '%d' % rnd.randint(0, 99), '%02d' % rnd.randint(0, 99),
                       '%d' % rnd.randint(1, 9999), '2020', '1970', '1969', '2038'])


def r_date():
    y, m, dd = r_year(), rnd.randint(0, 13), rnd.randint(0, 32)
    if rnd.random() < 0.8:
        m, dd = rnd.randint(1, 12), rnd.randint(1, 28)
    mon = rnd.choice(MONS)
    return rnd.choice([
        '%s-%02d-%02d' % (y, m, dd), '%s-%d-%d' % (y, m, dd), '%d/%d/%s' % (m, dd, y), '%d/%d' % (m, dd),
        '%s/%02d/%02d' % ('%04d' % rnd.randint(1000, 2100), m, dd), '%d %s %s' % (dd, mon, y), '%d %s' % (dd, mon),
        '%s %d' % (mon, dd), '%s %d, %s' % (mon, dd, y), '%d-%s-%s' % (dd, mon, y), '%s-%d-%s' % (mon, dd, y),
        '%04d%02d%02d' % (rnd.randint(1900, 2100), m, dd), '%02d%02d%02d' % (rnd.randint(0, 99), m, dd)])


def r_time():
    h, mi, s = rnd.randint(0, 24), rnd.randint(0, 60), rnd.randint(0, 61)
    if rnd.random() < 0.85:
        h, mi, s = rnd.randint(0, 23), rnd.randint(0, 59), rnd.randint(0, 59)
    frac = rnd.choice(['', '', '.5', '.123456789', ',25', '.0000000001'])
    return rnd.choice([
        '%d:%02d' % (h, mi), '%02d:%02d:%02d' % (h, mi, s), '%02d:%02d:%02d%s' % (h, mi, s, frac),
        '%d %s' % (rnd.randint(0, 13), rnd.choice(['am', 'pm', 'a.m.', 'P.M.'])),
        '%d:%02d%s' % (rnd.randint(0, 13), mi, rnd.choice(['am', ' pm', 'PM'])), '%02d%02d' % (h, mi),
        '%d:%02d%s' % (h, mi, rnd.choice(['+01', '-0530', '+05:30', 'Z', '+1', '-12:00']))])


def r_iso():
    y, m, dd = rnd.randint(1960, 2080), rnd.randint(1, 12), rnd.randint(1, 28)
    t = rnd.choice(['%02d' % rnd.randint(0, 23), '%02d:%02d' % (rnd.randint(0, 23), rnd.randint(0, 59)),
                    '%02d:%02d:%02d' % (rnd.randint(0, 23), rnd.randint(0, 59), rnd.randint(0, 59)),
                    '%02d:%02d:%02d.%d' % (rnd.randint(0, 23), rnd.randint(0, 59), rnd.randint(0, 59),
                                           rnd.randint(0, 999999))])
    z = rnd.choice(['', 'Z', '+01:00', '-0500', '+05', '+0530', '-03:30'])
    if t.isdigit() and not z:
        z = '+02'
    return '%04d-%02d-%02dT%s%s' % (y, m, dd, t, z)


def r_rel():
    n = rnd.choice(['1', '2', '10', '-1', '+3', '-36', '0', '400', '1.5', '-2.25', '+0.5'])
    u = rnd.choice(UNITS)
    if '.' in n:
        u = rnd.choice(['sec', 'seconds'])
    form = rnd.choice(['%s %s' % (n, u), '%s %s ago' % (n.lstrip('+-'), u), '%s %s' % (rnd.choice(
        ['next', 'last', 'this', 'third', 'first']), u), u, rnd.choice(['tomorrow', 'yesterday', 'today', 'now']),
        '%s %s hence' % (n.lstrip('+-'), u)])
    return form


def r_day():
    return rnd.choice(['%s', 'next %s', 'last %s', 'this %s', 'third %s', '%d %%s' % rnd.randint(0, 5)]) % rnd.choice(DAYS)


def r_zone():
    return rnd.choice(ZONES + ['%+03d' % rnd.randint(-14, 14), '%+05d' % (rnd.randint(-12, 14) * 100 + rnd.choice([0, 30, 45])),
                               'UTC%+d' % rnd.randint(-12, 12), '%+03d:%02d' % (rnd.randint(-12, 12), rnd.choice([0, 30]))])


def r_junk():
    return rnd.choice(['foo', '(c)', ',', '/', ':', '@5', 'T', 'DST', 'ago', 'pm', '5', '12', '-', 'x.y'])


FUZZ_WORDS = ['jan', 'sept.', 'mon', 'next', 'ago', 'hence', 'day', 'hours', 'utc', 'EST', 'DST', 'pm', 'a.m.',
              'T', 'Z', 'J', 'tomorrow', 'third', 'week', 'TZ="Asia/Tokyo"', 'TZ="', '9223372036854775807', '(', ')']


def fuzz_string():
    out = []
    for _ in range(rnd.randint(1, 14)):
        if rnd.random() < 0.25:
            out.append(rnd.choice(FUZZ_WORDS))
        else:
            out.append(rnd.choice('0123456789012345678901234567890+-:/.,@ ()\t'))
        if rnd.random() < 0.3:
            out.append(' ')
    return ''.join(out)


def random_case():
    if rnd.random() < 0.15:
        return rnd.choice(TZS[:8]), 'date %s-d %s %s' % ('--debug ' if rnd.random() < 0.5 else '', sq(fuzz_string()),
                                                          sq('+%F %T.%N %z %Z %s'))
    kinds = []
    parts = []
    n = rnd.randint(1, 4)
    for _ in range(n):
        k = rnd.choices(['date', 'time', 'iso', 'rel', 'day', 'zone', 'num', 'junk'], [5, 5, 2, 5, 2, 2, 1, 1])[0]
        kinds.append(k)
        parts.append({'date': r_date, 'time': r_time, 'iso': r_iso, 'rel': r_rel, 'day': r_day, 'zone': r_zone,
                      'num': lambda: str(rnd.choice([rnd.randint(0, 9999), rnd.randint(0, 99999999)])),
                      'junk': r_junk}[k]())
    s = ' '.join(parts)
    if rnd.random() < 0.1:
        s = s.upper()
    if rnd.random() < 0.05:
        s = 'TZ="%s" %s' % (rnd.choice(['Asia/Tokyo', 'UTC0', 'America/New_York', 'Europe/Helsinki']), s)
    if rnd.random() < 0.03:
        s = '@%d' % rnd.randint(-10 ** 10, 10 ** 10) + rnd.choice(['', '.5', ' x'])
    fmt = '+%F %T.%N %z %Z %s'
    debug = rnd.random() < 0.2
    return rnd.choice(TZS[:8]), 'date %s-d %s %s' % ('--debug ' if debug else '', sq(s), sq(fmt))


for _ in range(NRAND):
    tz, cmd = random_case()
    C(cmd, tz=tz, now=True)

NS_RE = re.compile(rb'(\d\d:\d\d:\d\d\.)\d{9}( [-+]\d{4} )')
FINAL_RE = re.compile(rb'(final: -?\d+\.)\d{9}( \(epoch-seconds\))')


def run(tz, cmd, which):
    env = dict(os.environ, LC_ALL='C', PATH=os.path.join(d, which) + ':' + os.environ.get('PATH', '/usr/bin:/bin'))
    env.pop('TZ', None)
    if tz is not None:
        env['TZ'] = tz
    p = subprocess.run(['bash', '-c', cmd], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    out, err = p.stdout, p.stderr
    if which == 'gnu' and 'help' in cmd and b'\nGNU coreutils online help' in out:
        out = out[:out.index(b'\nGNU coreutils online help')]
    if '--version' in cmd and 'cut' not in cmd and '/dev/full' not in cmd and 'echo' not in cmd:
        out = b''
    return p.returncode, out, err


def norm(r, s):
    # a time relative to "now" keeps the clock's nanoseconds
    rc, out, err = r
    return rc, NS_RE.sub(rb'\1N\2', out), FINAL_RE.sub(rb'\1N\2', err)


# Known differences, run and reported but not counted: nelibc's localtime_r
# fails for the last representable year (tm_year INT_MAX) in a zone west
# of UTC, where the UTC year has already overflowed.
KNOWN = [('America/New_York', 'date -d @67768036191676800'),
         ('America/New_York', "date -d '2147485547-12-31 23:59:59' +%s")]
# glibc applies a POSIX TZ rule (a TZ string, or a zone file's footer past
# its last transition) only from 1970: earlier times are standard time.
# Its rule arithmetic also overflows int past year 5885487. nelibc applies
# the rules to every year, so such a case is rerun in a zone without DST.
RULE_TZS = ('EST5EDT,M3.2.0,M11.1.0', 'NZST-12NZDT,M9.5.0,M4.1.0/3')
DST_TZS = RULE_TZS + ('America/New_York', 'Australia/Lord_Howe', 'Europe/Helsinki')
YEAR_RE = re.compile(rb'(?:^|\(Y-M-D\) |\n)([-+]?\d+)-\d\d-\d\d')


def glibc_rule_years(tz, cmd, results):
    zones = [tz] + re.findall(r'TZ="([^"]*)"', cmd)
    for r in results:
        for blob in (r[1], r[2]):
            for m in YEAR_RE.finditer(blob):
                y = int(m.group(1))
                for z in zones:
                    if (z in RULE_TZS and y <= 1970) or (z in DST_TZS and y > 5885000):
                        return True
    return False


bad = 0
rerun = 0
for tz, cmd, now in CASES:
    for attempt in range(3):
        g = run(tz, cmd, 'gnu')
        n = run(tz, cmd, 'nb')
        if g == n:
            break
        # GNU itself differs between runs: the result follows the clock
        g2 = run(tz, cmd, 'gnu')
        if g2 == n or (g != g2 and norm(g2, cmd) == norm(n, cmd)):
            g = n
            break
        if glibc_rule_years(tz, cmd, (g, n)) and attempt == 0:
            rerun += 1
            tz = 'Asia/Tokyo'
            cmd = re.sub(r'TZ="[^"]*"', 'TZ="Asia/Tokyo"', cmd)
    if g != n:
        bad += 1
        if bad <= 30:
            print('MISMATCH: TZ=%s %s' % (tz, cmd))
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:1500]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:1500]))
known = 0
for tz, cmd in KNOWN:
    g, n = run(tz, cmd, 'gnu'), run(tz, cmd, 'nb')
    if g != n:
        known += 1
    else:
        print('KNOWN DIFFERENCE GONE: TZ=%s %s' % (tz, cmd))
print('date_compare: %d cases, %d mismatches (%d rerun in Asia/Tokyo for glibc POSIX-rule years; %d known nelibc differences)'
      % (len(CASES), bad, rerun, known))
shutil.rmtree(d)
sys.exit(1 if bad else 0)

#!/usr/bin/env python3
"""Drive `nebox sh -i` on a pseudo-terminal and check interactive behavior:
line editing, history, completion, prompts, error recovery, signals.
Usage: tests/sh_interactive.py path/to/nebox"""
import os, pty, select, signal, sys, tempfile, time, struct, fcntl, termios

NEBOX = os.path.abspath(sys.argv[1])
UP, LEFT, HOME_KEY, DEL = '\x1b[A', '\x1b[D', '\x1b[H', '\x1b[3~'
failures = []


class Shell:
    def __init__(self, env_extra=None, cols=80, argv=('sh', '-i'), home=None):
        self.home = home or tempfile.mkdtemp(prefix='nebox-sh-i-')
        env = {'HOME': self.home, 'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
               'PS1': '$ ', 'TERM': 'xterm'}
        env.update(env_extra or {})
        env = {k: v for k, v in env.items() if v is not None}
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(self.home)
            os.execve(NEBOX, [NEBOX] + list(argv), env)
        self.pid, self.fd = pid, fd
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 24, cols, 0, 0))
        self.out = ''
        self.prompt()

    def read(self, timeout):
        r, _, _ = select.select([self.fd], [], [], timeout)
        if not r:
            return False
        try:
            data = os.read(self.fd, 65536)
        except OSError:
            return False
        if not data:
            return False
        self.out += data.decode('utf-8', 'replace')
        return True

    def expect(self, text, timeout=5.0):
        end = time.time() + timeout
        while text not in self.out:
            if time.time() > end or not self.read(max(0.0, end - time.time())):
                if text in self.out:
                    break
                raise AssertionError('expected %r, got %r' % (text, self.out[-400:]))
        i = self.out.index(text) + len(text)
        seen, self.out = self.out[:i], self.out[i:]
        return seen

    def prompt(self, timeout=5.0):
        # the editor turns bracketed paste on once per line read: a new prompt
        return self.expect('\x1b[?2004h', timeout)

    def send(self, s):
        os.write(self.fd, s.encode())

    def run(self, line, want, timeout=5.0):
        self.send(line + '\r')
        return self.expect(want, timeout)

    def close(self):
        try:
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(self.pid, 0)


def case(name):
    def wrap(fn):
        sh = None
        try:
            sh = fn()
            print('ok   %s' % name)
        except Exception as e:
            failures.append(name)
            print('FAIL %s: %s' % (name, e))
        return fn
    return wrap


@case('runs a command and shows the prompt again')
def _():
    sh = Shell()
    sh.run('echo hello', 'hello\r\n')
    sh.prompt()
    sh.close()


@case('syntax, expansion and special builtin errors return to the prompt')
def _():
    sh = Shell()
    sh.run('echo (', 'Syntax error')
    sh.prompt()
    sh.run('echo ${nope?gone}', 'gone')
    sh.prompt()
    sh.run('readonly R=1; R=2', 'read only')
    sh.prompt()
    sh.run('echo alive $?', 'alive 2')
    sh.close()


@case('PS2 for continuation lines; the whole command enters history')
def _():
    sh = Shell()
    sh.send('if true\r')
    sh.expect('> ')
    sh.run('then echo yes; fi', 'yes')
    sh.prompt()
    sh.send(UP)
    sh.expect('fi')
    sh.send('\x03')
    sh.prompt()
    sh.close()


@case('here-document lines are read with PS2')
def _():
    sh = Shell()
    sh.send('cat <<END\r')
    sh.expect('> ')
    sh.send('line one\r')
    sh.expect('> ')
    sh.send('END\r')
    sh.expect('line one\r\n')
    sh.prompt()
    sh.run('alias hi="echo aliased"', '\x1b[?2004l')
    sh.prompt()
    sh.run('hi', 'aliased\r\n')
    sh.close()


@case('history recall with Up and Ctrl-P, saved to $HISTFILE')
def _():
    sh = Shell()
    sh.run('echo one', 'one')
    sh.prompt()
    sh.run('echo two', 'two')
    sh.prompt()
    sh.send(UP + UP + '\r')
    sh.expect('one\r\n')
    sh.prompt()
    sh.send('\x10\r')
    sh.expect('one\r\n')
    sh.prompt()
    with open(os.path.join(sh.home, '.sh_history')) as f:
        hist = f.read().splitlines()
    # a line equal to the previous entry is not added again
    assert hist == ['echo one', 'echo two', 'echo one'], hist
    sh.close()


@case('history is loaded at startup and Ctrl-R searches it')
def _():
    home = tempfile.mkdtemp(prefix='nebox-hist-')
    hf = os.path.join(home, 'h')
    with open(hf, 'w') as f:
        f.write('echo alpha\necho beta\necho gamma\n')
    sh = Shell({'HISTFILE': hf})
    sh.send('\x12alp')
    sh.expect("(reverse-i-search)'alp': echo alpha")
    sh.send('\r')
    sh.expect('alpha\r\n')
    sh.close()


@case('editing keys: left, home, insert, delete, kill and yank')
def _():
    sh = Shell()
    sh.send('echo wrld' + LEFT * 3 + 'o\r')
    sh.expect('world\r\n')
    sh.prompt()
    sh.send('cho xy' + HOME_KEY + 'e' + '\x05' + '\x08z\r')
    sh.expect('xz\r\n')
    sh.prompt()
    sh.send('echo abc def\x17\x17echo \x19\r')
    sh.expect('abc def\r\n')
    sh.prompt()
    sh.send('echo kxeep' + LEFT * 4 + DEL + '\r')
    sh.expect('keep\r\n')
    sh.close()


@case('Ctrl-C discards the line; Ctrl-C ends a running loop')
def _():
    sh = Shell()
    sh.send('echo never')
    sh.send('\x03')
    sh.expect('^C')
    sh.prompt()
    sh.run('echo $?', '130')
    sh.prompt()
    sh.send('while :; do :; done\r')
    time.sleep(0.3)
    sh.send('\x03')
    sh.prompt()
    sh.run('echo back', 'back\r\n')
    sh.close()


@case('Ctrl-C reaches a foreground child, not the shell')
def _():
    sh = Shell()
    sh.send('sleep 5; echo after\r')
    time.sleep(0.3)
    sh.send('\x03')
    seen = sh.prompt(3)
    assert 'after\r\n' not in seen, seen
    sh.run('echo still here', 'still here')
    sh.close()


@case('completion: commands, builtins, files, variables')
def _():
    sh = Shell({'MYLONGVARIABLE': 'v'})
    sh.send('ech\t')
    sh.expect('echo ')
    sh.send('\x03')
    sh.prompt()
    open(os.path.join(sh.home, 'unique file.txt'), 'w').close()
    os.mkdir(os.path.join(sh.home, 'subdir'))
    sh.send('echo uni\t')
    sh.expect('unique\\ file.txt ')
    sh.send('\r')
    sh.expect('unique file.txt\r\n')
    sh.prompt()
    sh.send('cd sub\t')
    sh.expect('subdir/')
    sh.send('\r')
    sh.prompt()
    sh.run('pwd', 'subdir')
    sh.prompt()
    sh.send('echo $MYLONG\t')
    sh.expect('$MYLONGVARIABLE ')
    sh.send('\r')
    sh.expect('v\r\n')
    sh.close()


@case('double Tab lists ambiguous candidates')
def _():
    sh = Shell()
    for n in ('cand_a', 'cand_b'):
        open(os.path.join(sh.home, n), 'w').close()
    sh.send('echo cand_\t\t')
    sh.expect('cand_a')
    sh.expect('cand_b')
    sh.send('\x03')
    sh.close()


@case('PS1 gets parameter, arithmetic and command expansion and !')
def _():
    sh = Shell()
    sh.send("PS1='[$((1+2)) $(echo x) !]$ '\r")
    sh.expect('[3 x 2]$ ')
    sh.close()


@case('$- contains i; SIGTERM and SIGQUIT are ignored')
def _():
    sh = Shell()
    sh.run('case $- in *i*) echo interactive;; esac', 'interactive\r\n')
    sh.prompt()
    sh.run('kill -TERM $$; kill -QUIT $$; echo survived', 'survived\r\n')
    sh.close()


@case('$ENV is run at startup')
def _():
    home = tempfile.mkdtemp(prefix='nebox-env-')
    rc = os.path.join(home, 'rc')
    with open(rc, 'w') as f:
        f.write('greet() { echo hi from rc; }\n')
    sh = Shell({'ENV': rc})
    sh.run('greet', 'hi from rc')
    sh.close()


@case('long lines wrap and still edit')
def _():
    sh = Shell(cols=20)
    word = 'x' * 50
    sh.send('echo ' + word + LEFT * 10 + 'Y\r')
    sh.expect('x' * 40 + 'Y' + 'x' * 10 + '\r\n')
    sh.close()


@case('UTF-8 input moves by character')
def _():
    sh = Shell()
    sh.send('echo héllo' + LEFT * 3 + '\x7f' + 'e\r')
    sh.expect('hello\r\n')
    sh.close()


@case('Ctrl-D on an empty line exits with the last status')
def _():
    sh = Shell()
    sh.run('false', '\x1b[?2004l')
    sh.prompt()
    sh.send('\x04')
    sh.expect('exit')
    _, status = os.waitpid(sh.pid, 0)
    assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 1, status


@case('exit trap runs on exit')
def _():
    sh = Shell()
    sh.run("trap 'echo bye' EXIT", '\x1b[?2004l')
    sh.prompt()
    sh.send('exit\r')
    sh.expect('bye')
    sh.close()


@case('nsh: prompt with the directory, XDG history and rc')
def _():
    home = tempfile.mkdtemp(prefix='nebox-nsh-')
    os.makedirs(os.path.join(home, '.config', 'nsh'))
    with open(os.path.join(home, '.config', 'nsh', 'rc'), 'w') as f:
        f.write("alias ll='echo listing'\n")
    sh = Shell({'PS1': None}, argv=('nsh',), home=home)
    sh.expect('\x1b[1;36m~\x1b[0m $ ')
    sh.run('ll', 'listing\r\n')
    sh.prompt()
    os.mkdir(os.path.join(home, 'proj'))
    sh.run('cd proj', '\x1b[1;36mproj\x1b[0m $ ')
    with open(os.path.join(home, '.local', 'state', 'nsh', 'history')) as f:
        assert f.read().splitlines() == ['ll', 'cd proj']
    sh.run('echo (', 'nsh: line ')
    sh.close()


print('%d failed' % len(failures))
sys.exit(1 if failures else 0)

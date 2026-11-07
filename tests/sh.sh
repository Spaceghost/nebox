# sh conformance cases, sourced by tests/run.sh. The reference is dash
# (the container's /bin/sh) through a wrapper named sh on the reference PATH;
# `expect` cases pin choices where POSIX and dash disagree.
mkdir -p "$W/refbin"
DASH=$(command -v dash || echo /bin/sh)
printf '#!/bin/sh\nexec %s "$@"\n' "$DASH" > "$W/refbin/sh"
chmod +x "$W/refbin/sh"
REFPATH="$W/refbin:"

# shc NAME SCRIPT: run SCRIPT through `sh -c` (no single quotes in SCRIPT)
shc() { same "$1" "sh -c '$2'"; }
# shf NAME SCRIPT: run SCRIPT from a file operand
shf() { printf '%s\n' "$2" > "$W/fixture/case.sh"; same "$1" 'sh case.sh'; }
# shs NAME SCRIPT: script on standard input
shs() { printf '%s\n' "$2" > "$W/fixture/case.sh"; same "$1" 'sh < case.sh'; }
# shx NAME WANT SCRIPT: pinned output for a recorded choice (file operand)
shx() { printf '%s\n' "$3" > "$W/fixture/case.sh"; expect "$1" "$2" 'sh case.sh'; }

shc sh-echo 'echo hello world'
shc sh-status 'false; echo $?; true; echo $?'
shf sh-file-args 'echo "$0 $# $1"'

# invocation
expect sh-c-dollar0 'sh
exit=0' "sh -c 'echo \$0'"
same sh-c-name "sh -c 'echo \$0 \$1 \$#' myname a b"
same sh-c-dashdash "sh -c -- 'echo cx'"
same sh-ec "sh -ec 'echo \$-; false; echo nope'; echo st=\$?"
same sh-plus-e "sh +e -c 'false; echo pe'"
same sh-o-errexit "sh -o errexit -c 'false; echo nope'; echo st=\$?"
same sh-s-args "echo 'echo \"\$@\" \$#' | sh -s a b c"
same sh-missing-script "sh nonexistent_script 2>/dev/null; echo st=\$?"
same sh-c-missing "sh -c 2>/dev/null; echo st=\$?"
same sh-bad-option "sh -z -c 'echo z' 2>/dev/null; echo st=\$?"
same sh-bad-o "sh -o nosuch -c 'echo n' 2>/dev/null; echo st=\$?"
shs sh-stdin-script 'echo from stdin; echo "$#"'
shf sh-file-dollar0 'echo "$0"'
same sh-file-params "printf 'echo \"[\$1][\$2]\"\n' > p.sh; sh p.sh x y"
same sh-shebang-fallback "printf 'echo via shebang \$1\n' > s.sh; chmod +x s.sh; ./s.sh q; sh -c './s.sh r'"
same sh-hash-comment "sh -c '# comment only
echo a # trailing
echo b#notcomment'"

# quoting and tokens
shf sh-quote-single "echo 'a \$b \`c\` \\d'"
shf sh-quote-double 'x=1; echo "a $x \$x \"q\" \\ `echo c` \`"'
shf sh-quote-backslash 'echo a\ b \$x \"q\" \\ x\
y'
shf sh-quote-dq-backslash-other 'echo "a\qb\n" "\ "'
shf sh-quote-empty "set -- \"\" a '' b; echo \$#; for x in \"\$@\"; do echo \"[\$x]\"; done"
shf sh-quote-adjacent "echo \"a\"b'c'd\$((1+1))e"
shf sh-quote-newline-in-dq 'echo "line1
line2"'
shf sh-quote-sq-newline "echo 'l1
l2'"
shf sh-continuation 'echo one \
two
ec\
ho three'
shf sh-operators-adjacent 'echo a;echo b&&echo c||echo d;echo e|cat;(echo f);{ echo g; }'
shf sh-semicolon-trailing 'echo a; echo b;'
shf sh-io-number 'echo 2>/dev/null; echo 2 >/dev/null; echo "[$(echo 2 > f; cat f)]"'
shf sh-word-with-brace 'echo a{b,c} {x} }'
shf sh-bang-in-word 'echo a!b ! echo c'
shf sh-comment-in-quotes "echo \"a # b\" 'c # d' e#f"

# reserved words
shf sh-reserved-as-arg 'echo if then else fi do done case esac while until for in'
shf sh-reserved-quoted 'if true; then echo ok; fi; "if" true 2>/dev/null; echo st=$?'
shf sh-brace-word 'echo { }; { echo in; }'
shf sh-then-on-newline 'if true
then
  echo nl
fi'
shf sh-do-same-line 'for x in 1 2; do echo $x; done; for y in 3 4
do echo $y
done'
same sh-syntax-fi "sh -c 'echo a; fi' 2>/dev/null; echo st=\$?"
same sh-syntax-unterminated "sh -c 'if true; then' 2>/dev/null; echo st=\$?"
same sh-syntax-quote "sh -c 'echo \"x' 2>/dev/null; echo st=\$?"
same sh-syntax-paren "sh -c 'echo ) x' 2>/dev/null; echo st=\$?"
same sh-syntax-pipe-eof "sh -c 'echo line1
echo bad |' 2>/dev/null; echo st=\$?"
same sh-syntax-double-bang "sh -c '! ! true' 2>/dev/null; echo st=\$?"
same sh-syntax-fallthrough "sh -c 'case a in a) echo 1;& b) echo 2;; esac' 2>/dev/null; echo st=\$?"
same sh-syntax-badfunc "sh -c 'exit() { echo x; }' 2>/dev/null; echo st=\$?"

# here-documents
shf sh-heredoc-basic "x=1; cat <<EOF
a \$x \$(echo b) \\\$ \\\\ \`echo c\` 'q' \"d\"
EOF"
shf sh-heredoc-quoted "x=1; cat <<\"EOF\"
a \$x \$(echo b) \\\$ \\\\
EOF
cat <<'E'
b \$x
E
cat <<\\EOF
c \$x
EOF"
shf sh-heredoc-strip 'x=1; cat <<-EOF
		tab $x
	  space kept
	EOF
cat <<-"EOF"
	quoted $x
	EOF'
shf sh-heredoc-then-command 'cat <<EOF; echo after
in
EOF
echo end'
shf sh-heredoc-two 'cat <<E1 <<E2
one
E1
two
E2'
shf sh-heredoc-pipe 'cat <<EOF | tr a-z A-Z
piped $((1+2))
EOF'
shf sh-heredoc-redirect 'cat <<EOF > out
to file
EOF
cat out; cat <<EOF 2>/dev/null
err $(echo sub)
EOF'
shf sh-heredoc-in-loop 'for i in 1 2; do cat <<EOF
i=$i
EOF
done
while read x; do echo "r:$x"; done <<EOF
l1
l2
EOF'
shf sh-heredoc-delim-inside 'cat <<EOF
line with EOF inside
 EOF
EOF
echo done'
shf sh-heredoc-backslash-newline 'cat <<EOF
a\
b \$ \x \"
EOF'
shf sh-heredoc-space 'cat << EOF
spaced
EOF'
shf sh-heredoc-cmdsub 'x=$(cat <<EOF
hd
EOF
); echo "$x"; echo "$(cat <<E
inner
E
)"'
same sh-heredoc-eof "printf 'cat <<EOF\nabc\n' | sh; echo st=\$?"
shf sh-heredoc-function 'f() { cat <<EOF
in f $1
EOF
}
f a; f b'
shf sh-heredoc-expansion-ops 'x=; cat <<EOF
${x:-def} ${#x} $((2*3)) ${y=set} $y
EOF'
shf sh-heredoc-empty 'cat <<EOF
EOF
echo after'
shf sh-heredoc-big 'seq 1 20000 > big; cat <<EOF | wc -l
$(cat big)
EOF'

# aliases
shs sh-alias-basic 'alias e="echo al"
e hi
alias x="e "
x hi'
shs sh-alias-trailing-blank 'alias e="echo "
e if
alias nn=
nn echo z'
shs sh-alias-quoted-no 'alias e="echo al"
\e hi 2>/dev/null; echo st=$?
"e" hi 2>/dev/null; echo st=$?'
shs sh-alias-print 'alias a="echo x"
alias b=y
alias
alias a
alias nosuch; echo st=$?'
shs sh-alias-unalias 'alias e="echo al"
e hi
unalias e
e hi 2>/dev/null; echo st=$?
alias p=pwd q=echo
unalias -a
alias; echo st=$?
unalias nosuch; echo st=$?'
shs sh-alias-recursive 'alias echo="echo x"
echo y'
shs sh-alias-same-line 'alias z="echo z"; z 2>/dev/null; echo st=$?
z'
shs sh-alias-not-reserved 'alias if=echo
if true; then echo ok; fi'
shs sh-alias-newline-value 'alias m="echo a; echo b"
m'
shs sh-alias-in-function 'alias e="echo al"
f() { e in f; }
f'
shs sh-alias-arg-position 'alias e="echo al"
echo e; true e'

# parameter expansion (XCU 2.6.2, including the standard's examples)
shf sh-param-minus 'foo=asdf; echo ${foo-bar}xyz}; foo=; echo ${foo-bar}xyz}; unset foo; echo ${foo-bar}xyz}'
shf sh-param-colon-minus 'x=; echo ${x:-d} ${x-d}; x=v; echo ${x:-d} ${x-d}; unset x; echo ${x:-d} ${x-d}'
shf sh-param-assign 'unset x; echo ${x=def} $x; echo ${x=other} $x; y=; echo ${y:=cd} $y; echo ${y=zz}'
shf sh-param-plus 'unset x; echo "[${x+y}][${x:+y}]"; x=; echo "[${x+y}][${x:+y}]"; x=1; echo "[${x+y}][${x:+y}]"'
same sh-param-quest "sh -c 'echo \${1?custom}; echo after' 2>/dev/null; echo st=\$?; sh -c 'echo \${1?}; echo after' 2>/dev/null; echo st=\$?; sh -c 'x=; echo \${x:?}; echo after' 2>/dev/null; echo st=\$?; sh -c 'x=; echo \${x?}ok' 2>/dev/null; echo st=\$?"
shf sh-param-length 'x=/one/two/three; echo ${#x} ${#} ${#nope}; set -- a bb ccc; echo ${#1} ${#2} ${#3} ${##}'
shx sh-param-length-at '3 3
exit=0' 'set -- a bb ccc; echo ${#@} ${#*}'
shf sh-param-suffix 'x=file.c; echo ${x%.c}.o; x=posix/src/std; echo ${x%%/*}; echo ${x%/*}; x=a.b.c; echo ${x%.*} ${x%%.*} ${x%x}'
shf sh-param-prefix 'x=posix/src/std; echo ${x#*/}; echo ${x##*/}; x=/one/two/three; echo ${x#/}; echo ${x##*/}; echo ${x#x}'
shf sh-param-pattern-quoting 'x="a*b"; echo "${x%\*b}" ${x%"*b"} ${x%"$x"}; y="*"; echo ${x%$y} ${x%"$y"}; z="a[b"; echo ${z%\[b} ${z#a\[}'
shf sh-param-pattern-class 'x=abc123; echo ${x%%[0-9]*} ${x##[a-z]*} ${x#[[:alpha:]]} ${x%[[:digit:]]}'
shf sh-param-nested-default 'x=; echo "${x:-"a  b"}"; echo "${x:-'"'"'q'"'"'}"; echo ${x:-$(echo "c  d")}; echo "${x:-$(echo "c  d")}"; echo "${x:-\}}"; echo ${x:-\}}; y=z; echo "${x:-${y}}" ${x:-${y:-w}} ${x:-${x:-${x:-deep}}}'
shf sh-param-default-splitting 'unset x; for i in ${x:-"a b"}; do echo "[$i]"; done; for i in "${x:-a b}"; do echo "[$i]"; done; for i in ${x:-a b}; do echo "[$i]"; done; echo "${x-"a  b"}" ${x-"a  b"}'
shf sh-param-braces-adjacent 'x=ab; echo ${x}c $xc "${x}"c'
shf sh-param-positional 'set -- abc def; echo ${1#a} ${1%c} ${#1} ${10:-ten} ${11-eleven} ${2:+two}; set -- 1 2 3 4 5 6 7 8 9 10 11; echo $10 ${10} ${11} $#'
shf sh-param-special-hash 'echo $#; set -- a b c; echo $# ${#}; shift; echo $#'
shf sh-param-status 'false; echo $?; (exit 7); echo $?; x=$?; echo $x; true; echo "$?"'
shf sh-param-dollar-dash 'has() { case $- in *$1*) echo "$1=on";; *) echo "$1=off";; esac; }; has e; set -e; has e; set -u -f; has e; has u; has f; set +eu; has e; has u; has f; set -C -a; has C; has a; has x; case $- in *i*|*c*|*s*) echo nope;; *) echo clean;; esac'
shf sh-param-bang-pid 'echo "[$!]"; true & p=$!; wait $p; [ "$p" -gt 1 ] && echo positive; kill -0 $$ && echo self-alive'
shf sh-param-dollar-dollar '[ "$$" -gt 1 ] && echo pid; ( [ "$$" = "$(echo $$)" ] && echo same-in-subshell )'
shf sh-param-ppid '[ "$PPID" -gt 0 ] && echo ppid-set'
shx sh-param-lineno '1
3
in 5
exit=0' 'echo $LINENO

echo $LINENO
f() {
echo in $LINENO
}
f'
shf sh-param-at-quoted 'set -- a "" "b c"; for x in "$@"; do echo "[$x]"; done; for x in $@; do echo "[$x]"; done; echo "$#"'
shf sh-param-at-empty 'set --; for x in "$@"; do echo nope; done; for x in $@; do echo nope; done; set -- "$@"; echo $#; for x in "$*"; do echo "[$x]"; done'
shf sh-param-at-joined 'set -- 1 2; echo "x$@y"; for i in "$@"x; do echo "[$i]"; done; for i in x"$@"; do echo "[$i]"; done; for i in "$*"; do echo "[$i]"; done'
shx sh-param-at-empty-joined 'xy
[]
exit=0' 'set --; printf "%s\n" "x$@y"; set -- ""; printf "[%s]\n" "$@"'
shf sh-param-star-ifs 'set -- a b c; IFS=:; echo "$*"; echo $*; IFS=; echo "$*"; unset IFS; echo "$*"; IFS=" x"; echo "$*"'
shf sh-param-at-in-assignment 'set -- a b; x="$@"; echo "$x"; y="$*"; echo "$y"; z=$@; echo "$z"'
shx sh-param-at-pattern 'file main
c c
exit=0' 'set -- file.c main.c; echo ${@%.c}; echo "${@#*.}"'
shf sh-param-assign-special-error 'echo ${1=x} 2>/dev/null; echo st=$?'
shf sh-param-bad-substitution 'echo ${x} ok
echo ${1x} 2>/dev/null; echo st=$?'
same sh-param-missing-brace "sh -c 'echo \${x' 2>/dev/null; echo st=\$?; sh -c 'echo \${x:-a' 2>/dev/null; echo st=\$?"
shf sh-param-numeric-names 'echo ${0:+has0}; echo $9 ${9:-nine}; echo $0 | sed "s,.*/,,"'

# nounset
same sh-nounset-error "sh -c 'set -u; echo \$nope; echo after' 2>/dev/null; echo st=\$?"
shf sh-nounset-ok 'set -u; echo "$@" $*; set -- a; echo "$@" ${1} ${2:-two} ${#@}; x=; echo "[$x]"; echo ok'
same sh-nounset-length "sh -c 'set -u; echo \${#nope}' 2>/dev/null; echo st=\$?"

# command substitution
shf sh-cmdsub-basic 'echo $(echo a; echo b) "$(printf "x\n\n\n")" `echo c`; echo "[$(true)]" "[`true`]"'
shf sh-cmdsub-nested 'echo $(echo "$(echo inner)" ); echo `echo \`echo nest\``; echo $(echo $(echo $(echo deep)))'
shf sh-cmdsub-parens 'echo "$(echo "a)b")"; echo $(case x in x) echo c;; esac); echo $( (echo sub) ); echo $(echo "(" ")")'
shf sh-cmdsub-backquote-escapes 'echo `echo \\\\`; echo "`echo \"q\"`"; echo `echo \$HOME | sed "s,/.*,H,"`; echo "`echo \\\\$`"'
shf sh-cmdsub-status 'x=$(exit 3); echo $?; y=1 z=$(exit 4); echo $?; : $(exit 5); echo $?; echo $(exit 6); echo $?; echo "$(false)$(exit 9)"; echo $?'
shf sh-cmdsub-split 'x=$(printf "a b\nc"); echo $x; echo "$x"; for i in $(echo "1 2" 3); do echo "[$i]"; done'
shf sh-cmdsub-exit-inside 'x=$(echo a; exit 3); echo "$x $?"; echo $(exit 2); echo $?; f() { exit 5; }; (f); echo $?'
shf sh-cmdsub-vars-isolated 'x=1; y=$(x=2; echo $x); echo $x $y; cd / ; z=$(cd /tmp && pwd); pwd; echo $z'
shf sh-cmdsub-newlines 'x="$(printf "a\n\nb\n\n")"; printf "%s|" "$x"; echo; echo "$(echo)" | od -c | head -1'
shf sh-cmdsub-large 'x=$(seq 1 50000); echo "$x" | wc -l; echo ${#x}'
shf sh-cmdsub-empty 'echo "[$()]" $(); x=$( ); echo "[$x]"'
shf sh-cmdsub-redirect-inside 'echo $(echo a >&2) 2>/dev/null; echo $(cat <<E
h
E
)'
shf sh-cmdsub-with-pipe 'echo $(echo a b | tr a-z A-Z | cat)'

# arithmetic expansion
shf sh-arith-basic 'echo $((1+2)) $((2*3+4)) $(( (1+2)*3 )) $((10/3)) $((10%3)) $((-7/2)) $((-7%3)) $((7/-2)) $((2-5))'
shf sh-arith-precedence 'echo $((1+2*3)) $((2*3%4)) $((1<<4>>1)) $((5&3|8)) $((5^3&1)) $((1||0&&0)) $((!0+!1)) $((~0)) $((-(3))) $((+3)) $((2*-3))'
shf sh-arith-compare 'echo $((1<2)) $((1>=2)) $((1==1)) $((1!=1)) $((3>2>1)) $((2<=2)) $((0==0&&1==1))'
shf sh-arith-logical 'echo $((1&&0)) $((1||0)) $((0||0)) $((2&&3)) $(( 1 ? 2 : 3 )) $(( 0 ? 2 : 3 )) $(( 1 ? 0 ? 4 : 5 : 6 ))'
shf sh-arith-variables 'a=5; echo $((a)) $(($a)) $((a+1)) $((a*a)) $((b)) $((b+1)); unset c; echo $((c)); d=" 7 "; echo $((d))'
shf sh-arith-assign 'echo $((a=5)) $a $((a+=2)) $a $((a-=1)) $((a*=3)) $((a/=2)) $((a%=4)) $((a|=4)) $((a&=5)) $((a^=1)) $((a<<=2)) $((a>>=1)) $a; echo $((x = 1 ? 10 : 20)) $x'
shf sh-arith-bases 'echo $((010)) $((0x1f)) $((0X1F)) $((0)) $((00)) $((0xff+1)); x=0x10; echo $((x)); y=010; echo $((y))'
shf sh-arith-negative-var 'x=-5; echo $((x)) $((x*2)) $((-x)) $((0-x))'
shf sh-arith-big 'echo $((9223372036854775807)) $(( 9223372036854775807 + 1 )) $((1 - 2)) $((-9223372036854775807 - 1)) $((2147483648 * 4))'
shf sh-arith-shift-edge 'echo $((1<<63)) $((1<<62)) $((-1>>1)) $((-8>>1)) $((8>>10))'
shf sh-arith-nested 'echo $(( $((1+1)) + 1 )); echo $((1+$(echo 2))); echo $(( ${x:-3} * 2 )); x=4; echo $((x)) "$((x+1))"'
shf sh-arith-whitespace 'echo $((  1  +  2  )) $((
3 + 4
))'
same sh-arith-div-zero "sh -c 'echo \$((1/0)); echo after' 2>/dev/null; echo st=\$?; sh -c 'echo \$((1%0)); echo after' 2>/dev/null; echo st=\$?"
same sh-arith-syntax "sh -c 'echo \$((1 +)); echo after' 2>/dev/null; echo st=\$?; sh -c 'echo \$((08)); echo after' 2>/dev/null; echo st=\$?; sh -c 'echo \$(( \"3\" + 1 ))' 2>/dev/null; echo st=\$?"
same sh-arith-illegal-var "sh -c 'y=1+1; echo \$((y))' 2>/dev/null; echo st=\$?; sh -c 'y=abc; echo \$((y))' 2>/dev/null; echo st=\$?"
same sh-arith-missing-paren "sh -c 'echo \$((1+(2)); echo after' 2>/dev/null; echo st=\$?"
shf sh-arith-paren-group 'echo $(( ( 1 + 2 ) )) $((2)) $(((3))) $(( (1) ))'
shf sh-arith-quotes-literal 'echo $(( 1 + 2 )) "$(( 3 ))" "$(( 1 + 2 ))x"'
shx sh-arith-incdec '5 6 6 5 6
exit=0' 'x=5; echo $((x++)) $x $((x--)) $x $((x++, x--))'
shx sh-arith-comma '7 7
exit=0' 'echo $((1,2,3+4)) $((x=2, x*3+1))'
shf sh-arith-in-for 'for i in $((1+1)) $((2*2)); do echo $i; done; i=0; while [ $((i+=1)) -le 3 ]; do echo $i; done'
shf sh-arith-no-split 'IFS=1; echo $((11+100)) "$((11))"; x=$((123)); echo "$x"'

# tilde expansion
shf sh-tilde-home 'HOME=/h; echo ~ ~/x ~/ "~" a~b ~x/ "~/x" '"'"'~'"'"'; x=~:~/y; echo $x; x=a:~; echo $x'
shf sh-tilde-user 'echo ~root ~nosuchuser | sed "s,^/[^ ]*,HOME,"; echo ~root/x | sed "s,^/[^ ]*/,HOME/,"'
shf sh-tilde-quoted-no 'HOME=/h; echo \~ ~"x" "~"x; echo ~$x; y=~"/z"; echo "$y"'
shf sh-tilde-in-assignment 'HOME=/h; x=~; echo $x; PATH_LIKE=~/bin:~/sbin:/usr/bin; echo $PATH_LIKE; z=foo~; echo $z; w=":~"; echo $w'
shf sh-tilde-unset-home 'unset HOME; echo ~ ~/x'

# field splitting
shf sh-ifs-default 'x="  a  b	c
d  "; set -- $x; echo $#; for i in "$@"; do echo "[$i]"; done'
shf sh-ifs-colon 'IFS=:; set -- a:b::c:; for x in $*; do echo "[$x]"; done; echo "[$*]"; v="a:b::c:"; set -- $v; echo $#'
shf sh-ifs-mixed 'IFS=": "; v="a : b  c::d"; set -- $v; echo $#; for x in "$@"; do echo "[$x]"; done'
shf sh-ifs-leading-sep 'IFS=" :"; v=":a"; set -- $v; echo $# "[$1]"; v="a:"; set -- $v; echo $#; v=" a "; set -- $v; echo $#; v=":"; set -- $v; echo $# "[$1]"; v="::"; set -- $v; echo $#; v=" : "; set -- $v; echo $#'
shf sh-ifs-newline 'x="a
b"; for i in $x; do echo "[$i]"; done; IFS="
"; y="a b
c d"; for i in $y; do echo "[$i]"; done'
shf sh-ifs-empty-and-unset 'IFS=; x="a b"; for i in $x; do echo "[$i]"; done; unset IFS; for i in $x; do echo "[$i]"; done; IFS="x"; v="axbx"; for i in $v; do echo "[$i]"; done'
shf sh-ifs-mixed-quotes 'x="a b"; for i in $x"c d"$x; do echo "[$i]"; done; y=""; for i in $y; do echo nope; done; for i in "$y"; do echo "[$i]"; done; z=" "; for i in $z; do echo nope2; done; for i in $z"x"; do echo "[$i]"; done; for i in x$z; do echo "[$i]"; done'
shf sh-ifs-empty-expansions 'unset u; set -- $u; echo $#; set -- "$u"; echo $#; set -- ${u:-}; echo $#; set -- ${u:-""}; echo $#; set -- a${u}b; echo $#; set -- $u$u; echo $#; set -- ""; echo $#; set -- $(true); echo $#; set -- "$(true)"; echo $#; set -- $u"" ; echo $#'
shf sh-ifs-not-on-literals 'IFS=a; echo banana; x=banana; echo $x; echo "$x"'
shf sh-ifs-cmdsub 'IFS=,; for i in $(echo "a,b c"); do echo "[$i]"; done; unset IFS; for i in $(echo "a,b c"); do echo "[$i]"; done'
shf sh-ifs-arith 'IFS=2; echo $((121)) $((1+1)); for i in $((121)); do echo "[$i]"; done'
shf sh-ifs-assignment-nosplit 'x="a  b"; y=$x; echo "$y"; z=$x$x; echo "$z"'

# pathname expansion
same sh-glob-basic "touch a.c b.c .h c.h 'd e' '[x]'; sh -c 'echo *.c; echo *; echo .*; echo \"*\"; echo [a-b].c; echo \\[x\\]; echo \"[x]\"; echo [[]x]; echo *.nope; set -f; echo *.c; set +f; echo ?.c; echo */; echo [!a].c; echo [[:alpha:]].c; echo *.[ch]; echo [^a].c'"
same sh-glob-quoted-var "touch a.c b.c; sh -c 'x=\"*.c\"; echo \$x; echo \"\$x\"; echo \${x}; y=\"[a-b]\"; echo \$y.c; echo \"a\".c; echo a.\"c\" a\\.c; echo *.c/; echo \"\"*.c; echo *.c\"\"'"
same sh-glob-dirs "mkdir -p d1/s1 d2; touch d1/f d1/s1/x f1; sh -c 'echo */; echo */*; echo d*/s*/*; echo ./d1/*; echo d1/nope*; echo d[1]/f; echo \"d1\"/*; echo d1/\"f\"; echo */.; echo .; echo ..; echo .*; echo d*/; echo /nonexist*/x'"
same sh-glob-sort "touch B a A b _c 1; sh -c 'echo *; echo [a-z]*; echo [[:upper:]]*; echo [A-Z]*; echo [!A-Z]*'"
same sh-glob-dotfiles "touch .a .b c; sh -c 'echo *; echo .*; echo .[ab]; echo ?a; echo .?'"
same sh-glob-noglob "touch a.c; sh -c 'set -f; echo *.c; echo \$-; set +f; echo *.c; set -o noglob; echo *; set +o noglob; echo ?.c'"
same sh-glob-case-word "touch a.c; sh -c 'for f in *.c; do case \$f in *.c) echo c:\$f;; esac; done; x=\"*.c\"; case a.c in \$x) echo match;; esac; case \"*.c\" in \"\$x\") echo lit;; esac'"
same sh-glob-bracket-special "touch 'a-b' 'a]b' 'a\\\\b' ab; sh -c 'echo a[-]b; echo a[]]b; echo a[\\\\]b; echo a[\\\\-]b; echo a[!-]b | sort'"
same sh-glob-in-assignment-no "touch a.c b.c; sh -c 'x=*.c; echo \"\$x\"; echo \$x; y=\"*.c\"; echo \$y'"
same sh-glob-redirect-target-no "sh -c 'echo hi > a.c; echo x > \"*.c\"; cat \"*.c\"; ls'"
same sh-glob-escape-in-pattern "touch 'a*b' axb; sh -c 'echo a\\*b; echo \"a*b\"; echo a*b; p=\"a\\*b\"; echo \$p; echo a[*]b'"
same sh-glob-slash-in-bracket "mkdir d; touch d/x; sh -c 'echo d[/]x; echo d/*; echo \"d\"/x*; echo d/x[/]'"
same sh-glob-many "for i in \$(seq 1 300); do touch f\$i.txt; done; sh -c 'set -- *.txt; echo \$#; echo \$1 \$300' "

# simple commands and assignments
shf sh-assign-basic 'x=1; echo $x; x=2 y="a b"; echo "$x|$y"; z=; echo "[$z]"; a=1 b=$a; echo $b; c=$c:x; echo $c'
shf sh-assign-temp-external 'x=1; x=2 sh -c "echo \$x"; echo $x; x=3 env | grep "^x="; echo $x'
shf sh-assign-temp-builtin 'x=1; x=2 echo; echo $x; x=4 :; echo $x; x=5 eval echo; echo $x; f() { echo "f:$x"; }; x=6 f; echo $x'
shf sh-assign-temp-exported-to-function-child 'x=1; f() { sh -c "echo child:\$x"; }; x=7 f; echo $x'
shf sh-assign-status 'false; x=1; echo $?; false; x=$(true); echo $?; x=$(false); echo $?; y=$(exit 3) z=$(exit 4); echo $?'
shf sh-assign-not-command 'x=1 y=2; echo $x$y; echo x=3; "x=4"; echo st=$? $x' 
shf sh-assign-quoted-name-no 'a="x=1"; $a 2>/dev/null; echo st=$?; echo "[$x]"'
shf sh-assign-after-command 'echo a=1 b=2; true x=1; echo "[$x]"'
shf sh-assign-allexport 'set -a; v=1; sh -c "echo \$v"; set +a; w=2; sh -c "echo [\$w]"; export -p | grep "^export v="'
shf sh-assign-readonly 'readonly r=1; echo $r; (r=2) 2>/dev/null; echo st=$?; readonly s; echo "[$s]"; s=x 2>/dev/null; echo not-reached'
same sh-assign-readonly-exits "sh -c 'readonly x=1; x=2; echo after' 2>/dev/null; echo st=\$?; sh -c 'readonly x=1; unset x; echo after' 2>/dev/null; echo st=\$?"
shf sh-assign-tilde-and-cmdsub 'HOME=/h; x=~/$(echo a)/b; echo $x; y="~/c"; echo $y'
shf sh-command-word-expansion-order 'x=1; x=2 echo $x; echo $x; unset y; y=3 echo ${y:-unset}; echo "[${y}]"'
shf sh-null-command-redir '> created; [ -f created ] && echo made; x=1 > created2; [ -f created2 ] && echo made2 $x'
shf sh-command-with-slash 'printf "echo ext \$1\n" > ./cmd.sh; chmod +x cmd.sh; ./cmd.sh a; sh ./cmd.sh b'
shf sh-command-not-found 'nosuchcmd 2>/dev/null; echo st=$?; nosuch | cat; echo $?; echo x | nosuch 2>/dev/null; echo $?'
shf sh-command-not-executable 'echo data > notexec; ./notexec 2>/dev/null; echo st=$?; mkdir dir; ./dir 2>/dev/null; echo st=$?'
shf sh-path-search 'mkdir bin1; printf "echo one\n" > bin1/tool; chmod +x bin1/tool; PATH=$PWD/bin1:$PATH; tool; hash -r; PATH=/nonexistent; tool 2>/dev/null; echo st=$?; echo builtin ok'
shf sh-path-empty-entry 'printf "echo here\n" > tool2; chmod +x tool2; PATH=:/bin; tool2; PATH=/bin:; tool2'
shf sh-exit-status-range 'sh -c "exit 256"; echo $?; sh -c "exit 257"; echo $?; (exit 255); echo $?'

# redirections
shf sh-redir-output 'echo a > f; cat f; echo b >> f; cat f; echo c > f; cat f; echo "" > e; wc -c < e'
shf sh-redir-input 'printf "x\ny\n" > f; cat < f; read l < f; echo "$l"; while read l; do echo "r=$l"; done < f'
shf sh-redir-fd-numbers 'echo out 1>f; echo err 2>e 1>&2; cat f e; echo both >f 2>&1; cat f; echo swap 2>&1 1>/dev/null | cat'
shf sh-redir-dup-order 'echo x 2>&1 >/dev/null | cat; echo y >/dev/null 2>&1 | cat; echo z 1>&2 2>/dev/null; echo end'
shf sh-redir-exec 'exec 3>g; echo hi >&3; echo there 1>&3; exec 3>&-; cat g; echo zz >&3 2>/dev/null; echo st=$?; exec 4<g; read l <&4; echo $l; read l <&4; echo $l; exec 4<&-'
shf sh-redir-exec-stdout 'exec >eo; echo redirected; exec 2>&1; echo err >&2; exec >/dev/tty 2>/dev/null || exec 1>&2; cat eo 2>/dev/null || true'
shf sh-redir-noclobber 'echo a > f; set -C; echo b > f 2>/dev/null; echo "st=$?"; echo c >| f; cat f; echo d >> f; cat f; echo e > /dev/null; echo st=$?; set +C; echo f > f; cat f; : > f1; set -C; : > f1 2>/dev/null; echo st=$?; : >| f1; echo $?'
shf sh-redir-rdwr 'echo rw <> h; cat h; printf "abc" > i; exec 5<>i; read -r x <&5; echo "$x"; exec 5>&-'
shf sh-redir-close 'echo zz >&- 2>/dev/null; echo st=$?; exec 3>f; exec 3>&-; echo q >&3 2>/dev/null; echo st=$?'
shf sh-redir-bad-fd 'echo 1>&5 2>/dev/null; echo "st=$?"; cat <&7 2>/dev/null; echo st=$?'
shf sh-redir-errors 'echo no > /nonexist/x 2>/dev/null; echo "st=$?"; cat < nosuch 2>/dev/null; echo "st=$?"; echo after'
same sh-redir-special-builtin-error-exits "sh -c 'exec 3<nonexist; echo after' 2>/dev/null; echo st=\$?; sh -c ': <nonexist; echo after' 2>/dev/null; echo st=\$?; sh -c 'true <nonexist; echo after' 2>/dev/null; echo st=\$?; sh -c 'f() { :; }; f <nonexist; echo after' 2>/dev/null; echo st=\$?; sh -c '{ :; } <nonexist; echo after' 2>/dev/null; echo st=\$?"
shf sh-redir-compound 'for i in 1 2; do echo $i; done > fo; cat fo; if true; then echo t; fi 2>&1 | cat; while read l; do echo "l=$l"; done < fo; { echo x; } 2>/dev/null >fo; cat fo; (echo sub) > fo; cat fo; f() { cat; }; f < fo; case x in x) echo c;; esac > fo; cat fo; until false; do echo u; break; done > fo; cat fo'
shf sh-redir-function-def 'f() { echo in; } > fo; f; f; cat fo; g() { echo "$1"; } 2>/dev/null; g a'
shf sh-redir-builtin-restore 'echo a > f; echo b >&2 2>/dev/null; cd . > /dev/null; echo still; exec >f; echo redirected; exec 1>&2 2>/dev/null; echo c 2>/dev/null; cat f 2>/dev/null || true'
shf sh-redir-word-expansion 'n=f; echo a > $n; cat f; echo b > "${n}2"; cat f2; x=3; echo c >&$((x-2))'
shf sh-redir-tilde 'HOME=$PWD; echo home > ~/hf; cat hf'
shf sh-redir-dev-null 'echo x > /dev/null; set -C; echo y > /dev/null; echo st=$?'
shf sh-redir-exec-persists-children 'exec 3>f3; sh -c "echo child >&3"; exec 3>&-; cat f3'
shf sh-redir-nonexistent-dir-fd 'echo a 3>nonexist/x 2>/dev/null; echo st=$?'
shf sh-redir-append-create 'rm -f ap; echo a >> ap; echo b >> ap; cat ap'
shf sh-redir-here-and-redirect-order 'cat <<EOF >hf 2>&1
body
EOF
cat hf'
shf sh-redir-saved-fd-not-inherited 'echo a > f; { ls /proc/self/fd 2>/dev/null | sort -n | tail -1; } > /dev/null; sh -c "ls /proc/self/fd | wc -l" > n1; (exec 3>&-; ls /proc/self/fd | wc -l) > n2; echo done'

# pipelines
shf sh-pipe-basic 'echo a | cat; printf "b\nc\n" | sort -r | cat; echo x | cat | cat | cat'
shf sh-pipe-status 'true | false; echo $?; false | true; echo $?; (exit 5) | (exit 6) | (exit 7); echo $?; exit 7 | true; echo $?'
shf sh-pipe-negate '! true; echo $?; ! false; echo $?; ! true | false; echo $?; ! false | true; echo $?; ! echo neg | cat; echo $?'
shf sh-pipe-subshell-vars 'x=1; echo | x=2; echo $x; echo a | read y; echo "[$y]"; x=3 | cat; echo $x'
shf sh-pipe-builtins 'echo a | { read x; echo "got $x"; }; echo b | while read l; do echo "w:$l"; done; printf "1\n2\n" | { read a; read b; echo $b$a; }'
shf sh-pipe-large 'seq 1 100000 | wc -l; seq 1 100000 | tail -1; yes | head -5 | wc -l'
shf sh-pipe-multiline 'echo a |
cat |
  cat'
shf sh-pipe-signal-status 'sh -c "kill -9 \$\$" 2>/dev/null; echo $?; (kill -TERM $$) 2>/dev/null; echo $?; sh -c "kill -USR1 \$\$" 2>/dev/null; echo $?'
shf sh-pipe-exit-in-component 'echo a | { exit 3; }; echo $?; { echo b; exit 4; } | cat; echo $?'
shf sh-pipe-redirect-in-component 'echo a 2>&1 | cat; cat < /dev/null | wc -c; echo b | cat > pf; cat pf'

# lists
shf sh-list-and-or 'true && echo a; false && echo nope; false || echo b; true || echo nope; true || echo a && echo c; false || echo d && false || echo e; true && false || echo f; echo $?'
shf sh-list-and-or-status 'true && false; echo $?; false || false; echo $?; false && true; echo $?; true || false; echo $?'
shf sh-list-sequence 'echo a; echo b; false; echo $?'
shf sh-list-async 'echo a & wait; echo b; (sleep 0.2; echo late) & echo c; wait; echo d; sleep 5 & kill $!; wait $!; echo "st=$?"'
shf sh-list-async-stdin 'echo input | { cat & wait; echo "[done]"; }'
shf sh-list-async-status 'false & echo $?; wait $!; echo $?; (exit 3) & wait $!; echo $?'
shf sh-list-newlines 'echo a &&
echo b ||
echo c
echo d |
cat'
shf sh-list-and-or-pipeline 'echo a | grep -q a && echo found || echo missing; echo b | grep -q z && echo found || echo missing'
shf sh-list-bg-pid-dollar-bang 'sleep 1 & p=$!; [ "$p" -gt 0 ] && echo got-pid; kill $p; wait $p; echo $?'

# compound commands
shf sh-if-elif 'if false; then echo 1; elif false; then echo 2; elif true; then echo 3; else echo 4; fi; if false; then echo x; fi; echo $?; if true; then false; fi; echo $?; if false; then :; else false; fi; echo $?'
shf sh-if-nested 'if true; then if false; then echo a; else echo b; fi; fi; if (exit 1); then echo c; elif (exit 0); then echo d; fi'
shf sh-if-status-of-cond 'if (exit 3); then :; fi; echo $?; if false; then :; fi; echo $?'
shf sh-while-until 'i=0; while [ $i -lt 3 ]; do echo $i; i=$((i+1)); done; i=0; until [ $i -ge 3 ]; do echo $i; i=$((i+1)); done; while false; do :; done; echo $?; until true; do :; done; echo $?'
shf sh-while-read 'printf "a\nb\n" | while read x; do echo "<$x>"; done; printf "1 2\n3 4\n" | while read a b; do echo "$b$a"; done'
shf sh-while-status 'i=0; while [ $i -lt 2 ]; do i=$((i+1)); (exit $i); done; echo $?; while true; do break; done; echo $?'
shf sh-for-basic 'for x in a b c; do echo $x; done; for x in; do echo nope; done; echo $?; for x in "a b" c; do echo "[$x]"; done; for x in $(echo 1 2) "$(echo 3 4)"; do echo "[$x]"; done'
shf sh-for-without-in 'set -- p q; for x; do echo "[$x]"; done; for x
do echo "<$x>"; done; f() { for a; do echo "f:$a"; done; }; f 1 2'
shf sh-for-status 'for x in 1 2; do (exit $x); done; echo $?; for x in; do :; done; echo $?; false; for x in 1; do :; done; echo $?'
shf sh-for-var-persists 'for x in 1 2 3; do :; done; echo $x; for y in $nothing; do :; done; echo "[$y]"'
shf sh-break-continue 'for i in 1 2 3; do for j in a b; do if [ $j = b ]; then continue 2; fi; echo $i$j; done; done; i=0; while [ $i -lt 5 ]; do i=$((i+1)); [ $i = 2 ] && continue; [ $i = 4 ] && break; echo $i; done; for i in 1 2; do for j in 1 2; do break 2; done; echo nope; done; echo end'
shf sh-break-outside 'break; echo "st=$?"; continue; echo "st=$?"; for i in 1; do break 5; done; echo ok'
same sh-break-bad-arg "sh -c 'break x; echo after' 2>/dev/null; echo st=\$?; sh -c 'continue 0; echo after' 2>/dev/null; echo st=\$?"
shf sh-break-in-function 'for i in 1 2; do f() { break; }; f; echo after-f $i; done'
shf sh-case-basic 'case abc in a*) echo 1;; *) echo 2;; esac; case "a b" in "a b") echo q;; esac; case x in (x) echo paren;; esac; case y in a|y) echo alt;; esac; case "" in "") echo empty;; esac; case foo in f?o) echo q;; esac'
shf sh-case-patterns 'x="*"; case abc in $x) echo glob;; esac; case "*" in "$x") echo lit;; esac; case abc in "$x") echo no;; *) echo else;; esac; case a.c in *.[ch]) echo src;; esac; case A in [[:upper:]]) echo up;; esac; case - in [a-]) echo dash;; esac'
shf sh-case-nomatch-status 'case x in y) echo no;; esac; echo $?; case x in x) false;; esac; echo $?; case x in x) ;; esac; echo $?'
shf sh-case-multiline 'case b in
  a) echo a ;;
  b)
    echo b
    ;;
  c) echo c
esac'
shf sh-case-esac-pattern 'case esac in (esac) echo matched;; esac; case in in in) echo in;; esac'
shf sh-case-word-expansion 'x="a b"; case $x in "a b") echo one-word;; esac; case "$(echo c)" in c) echo c;; esac; case $((1+1)) in 2) echo two;; esac'
shf sh-case-quoted-special 'case "a]b" in a]b) echo q;; esac; case "[" in "[") echo bracket;; esac; case "\\" in "\\") echo bs;; esac; case x in \x) echo esc;; esac'
shf sh-brace-group '{ echo a; echo b; } > fo; cat fo; { echo c
}
echo d; { false; }; echo $?'
shf sh-subshell 'x=1; (x=2; echo $x); echo $x; (cd /; pwd); pwd | sed "s,.*/,,"; (exit 3); echo $?; (echo in; exit 4); echo $?; ( (echo nested) )'
shf sh-subshell-traps-reset 'trap "echo t" EXIT; (echo sub); echo main; (trap "echo subt" EXIT; echo sub2); echo end'
shf sh-subshell-redirect '(echo a; echo b) > so; cat so; (cat) < so'
shf sh-compound-in-pipeline 'for i in 1 2; do echo $i; done | cat; { echo a; echo b; } | wc -l; if true; then echo t; fi | cat'

# functions
shf sh-func-basic 'f() { echo "f:$# $1 $2"; return 5; }; f a b; echo $?; g() { f x y; }; g; echo "$#"'
shf sh-func-recursion 'fact() { if [ $1 -le 1 ]; then echo 1; else echo $(( $1 * $(fact $(($1 - 1))) )); fi; }; fact 10; fib() { if [ $1 -lt 2 ]; then echo $1; else echo $(( $(fib $(($1-1))) + $(fib $(($1-2))) )); fi; }; fib 10'
shf sh-func-params-restored 'f() { shift; echo "$@"; }; f 1 2 3; set -- p q; f; echo "$@"; g() { set -- x y; echo $#; }; g; echo $# $1'
shf sh-func-return 'r() { return; }; false; r; echo $?; h() { echo $?; }; (exit 3); h; k() { return 7; echo nope; }; k; echo $?; m() { false; }; m; echo $?; n() { true; }; n; echo $?'
shf sh-func-return-in-loop 'f() { for i in 1 2 3; do [ $i = 2 ] && return 9; echo $i; done; echo nope; }; f; echo $?'
shf sh-func-unset 'f() { echo f; }; f; unset -f f; f 2>/dev/null; echo st=$?; g() { echo g1; }; g() { echo g2; }; g'
shf sh-func-forms 'func() ( echo subfunc; x=2 ); x=1; func; echo $x; k() { echo k; } > /dev/null; k; echo after-k; w() for a in 1 2; do echo w$a; done; w; i() if true; then echo iff; fi; i'
shf sh-func-newline-body 'f()
{
  echo multi
}
f'
shf sh-func-vars-global 'f() { v=set-in-f; }; f; echo $v; g() { unset v; }; g; echo "[$v]"'
shf sh-func-nested-def 'outer() { inner() { echo inner; }; inner; }; outer; inner'
shf sh-func-name-same-as-command 'echo() { printf "my echo %s\n" "$*"; }; echo hi; unset -f echo; echo back'
shf sh-func-exit 'f() { exit 3; }; (f); echo $?; g() { echo before; exit 4; echo nope; }; g; echo nope2'
shf sh-func-redirect-call 'f() { echo "$1"; cat; }; echo in | f a; f b < /dev/null; f c > fo; cat fo'
shf sh-func-positional-dollar0 'f() { echo "$0" | sed "s,.*/,,"; echo $#; }; f 1 2 3'
shf sh-func-command-builtin 'cd() { echo mycd; }; cd /; command cd /tmp; pwd; pwd() { echo mypwd; }; pwd; command pwd | sed "s,.*,P,"; unset -f cd pwd'
shf sh-func-args-with-spaces 'f() { for a in "$@"; do echo "[$a]"; done; echo $#; }; f "a b" "" c'
shf sh-func-local-via-subshell 'f() ( x=inner; echo $x ); x=outer; f; echo $x'
shf sh-func-deep-recursion 'count() { if [ $1 -gt 0 ]; then count $(($1 - 1)); else echo bottom; fi; }; count 200'

# special built-ins
shf sh-colon 'if :; then echo ok; fi; : "$(echo side)" > fo; echo $?; : a b c'
shf sh-dot-basic 'printf "echo sourced \$1 \$#\nx=from-dot\n" > d.sh; set -- p q; . ./d.sh; echo $x; echo "$@"'
shf sh-dot-return 'printf "echo one\nreturn 4\necho nope\n" > d.sh; . ./d.sh; echo "after $?"'
shf sh-dot-functions-persist 'printf "fd() { echo fd; }\nalias al=echo\n" > d.sh; . ./d.sh; fd'
same sh-dot-missing "sh -c '. /nonexist; echo after' 2>/dev/null; echo st=\$?; sh -c '. nosuch_file_in_path; echo after' 2>/dev/null; echo st=\$?"
shf sh-dot-path-search 'mkdir lib; printf "echo from path\n" > lib/inc.sh; PATH=$PWD/lib:$PATH; . inc.sh'
shf sh-dot-nested 'printf ". ./d2.sh\necho d1\n" > d1.sh; printf "echo d2\n" > d2.sh; . ./d1.sh'
shf sh-dot-exit 'printf "echo in\nexit 6\n" > d.sh; . ./d.sh; echo nope'
shf sh-eval-basic 'x="a b"; eval echo \$x; eval "y=\"$x\""; echo "[$y]"; eval; echo "st=$?"; eval "echo one; echo two"; eval echo \$x \| cat'
shf sh-eval-exit-status 'eval false; echo $?; eval "exit 7"; echo nope'
shf sh-eval-quoting 'a="1 2"; eval "set -- $a"; echo $#; eval "set -- \"$a\""; echo $#; cmd="echo"; args="x  y"; eval "$cmd $args"; eval "$cmd \"$args\""'
shf sh-eval-syntax-error 'eval "echo ok"; eval "(" 2>/dev/null; echo nope'
shf sh-eval-multiline 'eval "echo a
echo b"; eval "f() { echo ef; }"; f'
shf sh-eval-loop 'i=0; while [ $i -lt 100 ]; do eval "v$i=$i"; i=$((i+1)); done; echo $v42 $v99'
shf sh-exec-no-command 'exec >eo; echo redirected; exec 3>f3; echo three >&3; exec 3>&-; cat f3 >&2 2>/dev/null; exec 1>&2 2>/dev/null; cat eo 2>/dev/null; echo done 2>/dev/null'
same sh-exec-command "sh -c 'exec echo replaced; echo nope'; echo st=\$?; sh -c 'exec nosuch; echo nope' 2>/dev/null; echo st=\$?; sh -c 'exec /etc/passwd; echo nope' 2>/dev/null; echo st=\$?"
shf sh-exec-args-env 'x=1; (exec sh -c "echo \$x [\$y]"); y=2 exec sh -c "echo \$x \$y"'
same sh-exit-codes "sh -c 'exit 3'; echo \$?; sh -c 'exit'; echo \$?; sh -c 'false; exit'; echo \$?; sh -c 'exit abc; echo after' 2>/dev/null; echo st=\$?; sh -c 'exit -1' 2>/dev/null; echo st=\$?; sh -c 'exit 3 4; echo after' 2>/dev/null; echo st=\$?"
shf sh-exit-in-subshell-only '(exit 3); echo $?; x=$(exit 2; echo nope); echo $?; { (exit 1); echo after-sub; }'
shf sh-export 'export x; x=5; env | grep "^x="; export y=1 z; echo $y; z=2; env | grep "^z="; export -p | grep "^export x"; export x=6; env | grep "^x="; unset x; export -p | grep "^export x" ; echo end'
same sh-export-bad-name "sh -c 'export 1x=2; echo after' 2>/dev/null; echo st=\$?; sh -c 'readonly 1x; echo after' 2>/dev/null; echo st=\$?; sh -c 'unset 1x; echo after' 2>/dev/null; echo st=\$?"
shf sh-readonly-print 'readonly a=1; b=2; readonly b; readonly c; readonly -p | grep -E "^readonly (a|b|c)"; readonly | grep -c "^readonly a="'
shf sh-readonly-export 'readonly r=1; export r; sh -c "echo \$r"; export -p | grep "^export r="'
shf sh-set-positional 'set -- -a b; echo "$1 $2"; set -e -- x; echo "$1"; set x y z; echo $#; set --; echo $#; set -- ; echo $#; set -e; set -; echo "e still: $-" | grep -c e; set +e; set -- "a b" c; echo $# "$1"'
shf sh-set-print-vars 'unset FOO; a=1; b="x y"; c="it'"'"'s"; set | grep -E "^(a|b|c)="; set | grep -c "^IFS="'
shf sh-set-options 'set -o nounset; case $- in *u*) echo u;; esac; set +o nounset; case $- in *u*) echo nope;; *) echo nou;; esac; set -o errexit -o noglob; case $- in *e*f*|*f*e*) echo ef;; esac; set +o errexit; set -o | grep -E "^(noglob|errexit) " | sed "s/  */ /g"; set +o | grep -E "^set [-+]o (noglob|errexit)$"'
same sh-set-bad-option "sh -c 'set -o nosuch; echo after' 2>/dev/null; echo st=\$?; sh -c 'set -z; echo after' 2>/dev/null; echo st=\$?"
shf sh-set-noexec 'echo ok; set -n; echo nope; syntax error ((('
same sh-set-n-syntax "sh -nc 'echo nope; syntax error (((' 2>/dev/null; echo st=\$?; sh -n case.sh 2>/dev/null; echo st=\$?"
shf sh-set-xtrace 'x=1; set -x; echo $x "a b"; set +x; echo done; PS4="++ "; set -x; y=2; echo hi; set +x' 
same sh-set-xtrace-stderr "sh -xc 'x=1; echo \$x' 2>&1"
same sh-set-verbose "printf 'echo a\necho b\n' | sh -v 2>&1"
shf sh-set-u-with-positional 'set -u; set -- a; echo $1; echo ${2:-none}; echo $#; echo "$@"; echo ok'
same sh-set-u-unset-positional "sh -uc 'echo \$1; echo nope' 2>/dev/null; echo st=\$?"
same sh-shift "sh -c 'set -- a b c; shift; echo \$1 \$#; shift 2; echo \$#; shift 0; echo \$#; shift; echo nope' 2>/dev/null; echo st=\$?; sh -c 'shift 2; echo after' 2>/dev/null; echo st=\$?; sh -c 'shift x' 2>/dev/null; echo st=\$?"
shf sh-times-format 'times | sed "s/[0-9]/N/g"; times x 2>/dev/null; echo st=$?'
shf sh-unset-basic 'x=1; f() { :; }; unset x f; echo "[$x]"; unset -f f; f 2>/dev/null; echo st=$?; unset -v nosuchvar; echo $?; unset; echo $?; y=2; unset -v y; echo "[$y]"; z=3; unset -f z; echo $z'
same sh-unset-readonly "sh -c 'readonly r; unset r; echo after' 2>/dev/null; echo st=\$?"
shf sh-special-builtin-assign-persists 'x=1 :; echo $x; x=2 eval echo; echo $x; x=3 export x; sh -c "echo \$x"; x=4 readonly x; echo $x'
same sh-special-builtin-via-command "sh -c 'command shift 5; echo after \$?' 2>/dev/null; sh -c 'command exec 3<nonexist; echo after2 \$?' 2>/dev/null; sh -c 'command eval \"(\"; echo after3 \$?' 2>/dev/null"

# regular built-ins
shf sh-cd-basic 'cd sub; pwd | sed "s,.*/,,"; cd deep; pwd | sed "s,.*/,,"; cd ..; pwd | sed "s,.*/,,"; cd ../..; cd nosuch 2>/dev/null; echo st=$?; cd /; pwd; cd /tmp; echo $PWD $OLDPWD; cd -; pwd'
shf sh-cd-home 'HOME=$PWD/sub; cd; pwd | sed "s,.*/,,"; cd /; HOME=; cd 2>/dev/null; echo st=$?; unset HOME; cd 2>/dev/null; echo st=$?'
shf sh-cd-cdpath 'CDPATH=$PWD/sub; cd deep | sed "s,.*/,,"; pwd | sed "s,.*/,,"; cd /; CDPATH=nonexist:$OLDPWD/../sub; cd deep | sed "s,.*/,,"; cd /; CDPATH=sub; cd deep 2>/dev/null; echo st=$?; cd "$OLDPWD" >/dev/null; cd ./sub; pwd | sed "s,.*/,,"'
shf sh-cd-logical 'mkdir -p a/b; ln -s a/b link2; cd link2; pwd | sed "s,.*/fixture,F,;s,.*/got,F,;s,.*/ref,F,"; cd ..; pwd | sed "s,.*/,,"; cd link2; cd -P .; pwd | sed "s,.*/,,"; cd ../..; pwd | sed "s,.*/,,"'
shf sh-cd-physical 'mkdir -p a/b; ln -s a/b link2; cd -P link2; pwd | sed "s,.*/,,"; echo "$PWD" | sed "s,.*/,,"; cd -L ..; pwd | sed "s,.*/,,"'
shf sh-cd-dash-prints 'cd sub; cd - | sed "s,.*/,,"; cd - | sed "s,.*/,,"; cd - > /dev/null; pwd | sed "s,.*/,,"'
shf sh-cd-dotdot-canonical 'cd sub/deep/../deep; pwd | sed "s,.*/,,"; echo "$PWD" | sed "s,.*/sub/,,"; cd ./../.; pwd | sed "s,.*/,,"'
shf sh-cd-options 'cd -x 2>/dev/null; echo st=$?; pwd -x 2>/dev/null; echo st=$?; cd -- sub; pwd | sed "s,.*/,,"'
shf sh-pwd 'pwd | sed "s,.*/,,"; cd sub; pwd -L | sed "s,.*/,,"; pwd -P | sed "s,.*/,,"; PWD=/bogus; pwd | sed "s,.*/,,"'
shf sh-command-v 'f() { :; }; alias ll="ls -l"
command -v f; command -v if; command -v nosuch; echo st=$?; command -v ll; command -v cd; command -v echo; command -v cat | sed "s,/.*/,/P/,"; command -v ./case.sh; command -v nosuch/x; echo st=$?'
shf sh-command-V 'f() { :; }; alias ll="ls -l"
command -V f; command -V if; command -V echo; command -V ll; command -V cd; command -V nosuch; echo st=$?; command -V cat | sed "s, /.*, PATH,"'
shf sh-type 'f() { :; }; alias ll="ls -l"
type f; type if; type echo; type ll; type cd; type nosuch; echo st=$?; type cat | sed "s, /.*, PATH,"; type set; type f if; type; echo st=$?'
shf sh-command-exec 'f() { echo func; }; command f; cd() { echo mycd; }; cd /; command cd /tmp; pwd; command echo via-command; command -p echo p; command nosuch 2>/dev/null; echo st=$?; command; echo st=$?; command -v; echo st=$?'
shf sh-command-p 'PATH=/nonexist; command -p cat /dev/null; echo st=$?; command -p -v cat | sed "s,/.*/,/P/,"; cat /dev/null 2>/dev/null; echo st=$?'
shf sh-getopts-loop 'while getopts ab:c opt -a -b val -c -d x 2>/dev/null; do echo "$opt [$OPTARG] $OPTIND"; done; echo "end $OPTIND $opt"'
shf sh-getopts-grouped 'set -- -ab -c arg; while getopts abc o; do echo "$o $OPTIND"; done; echo "rest $OPTIND ${!OPTIND:-x}" 2>/dev/null || true; shift $((OPTIND-1)); echo "$@"'
shf sh-getopts-silent 'OPTIND=1; set -- -x; getopts :ab opt; echo "$opt [$OPTARG]"; OPTIND=1; set -- -b; getopts :b: opt; echo "$opt [$OPTARG]"; OPTIND=1; getopts b: opt 2>/dev/null; echo "$opt [$OPTARG] $?"'
shf sh-getopts-end 'set -- -a -- -b; getopts ab o; echo $o; getopts ab o; echo "$? $o $OPTIND"; set -- x -a; OPTIND=1; getopts ab o; echo "$? $OPTIND"; set --; OPTIND=1; getopts ab o; echo "$?"'
shf sh-getopts-optarg-attached 'set -- -bval -a; getopts ab: o; echo "$o [$OPTARG] $OPTIND"; getopts ab: o; echo "$o [$OPTARG] $OPTIND"'
shf sh-getopts-positional-default 'set -- -a -b x rest; while getopts ab: o; do echo "$o:$OPTARG"; done; shift $((OPTIND - 1)); echo "$# $1"'
shf sh-getopts-reset 'set -- -a -b; getopts ab o; echo $o; OPTIND=1; getopts ab o; echo $o $OPTIND; OPTIND=2; getopts ab o; echo $o'
same sh-getopts-usage "sh -c 'getopts; echo after \$?' 2>/dev/null; sh -c 'getopts a; echo after \$?' 2>/dev/null"
shf sh-hash 'hash -r; hash cat ls; hash | sed "s,/.*/,/P/," | sort; hash -r; hash; echo st=$?; hash nosuchcmd 2>/dev/null; echo st=$?; hash echo; hash | wc -l'
shf sh-kill 'sleep 10 & p=$!; kill $p; wait $p; echo $?; sleep 10 & p=$!; kill -s KILL $p; wait $p; echo $?; sleep 10 & p=$!; kill -9 $p; wait $p; echo $?; sleep 10 & p=$!; kill -TERM $p; wait $p; echo $?; kill -0 $$; echo $?'
shf sh-kill-l 'kill -l 15; kill -l 143; kill -l 9; kill -l 2 1; kill -l | head -3; kill -l HUP 2>/dev/null; echo st=$?'
same sh-kill-errors "sh -c 'kill; echo after \$?' 2>/dev/null; sh -c 'kill -s NOPE 1; echo after \$?' 2>/dev/null; sh -c 'kill 999999; echo after \$?' 2>/dev/null; sh -c 'kill -l 300; echo after \$?' 2>/dev/null"
shf sh-read-basic 'printf "a b  c\n" | { read x y; echo "[$x][$y]"; }; printf "x\n" | { read; echo "[$REPLY]"; echo st=$?; }; printf " a b \n" | { read x; echo "[$x]"; }'
shf sh-read-backslash 'printf "a\\\\\nb c\n" | { read x; echo "[$x]"; }; printf "a\\\\nb\n" | { read -r x; echo "[$x]"; read -r y; echo "st=$?"; }; printf "a\\\\ b c\n" | { read x y; echo "[$x][$y]"; }; printf "a\\\\:b\n" | { IFS=: read x y; echo "[$x][$y]"; }'
shf sh-read-eof 'printf "  a  b  " | { read x y z; echo "st=$? [$x][$y][$z]"; }; read x < /dev/null; echo "st=$? [$x]"; printf "nonl" | { read x; echo "$? $x"; }'
shf sh-read-ifs 'printf "a:b:c\n" | { IFS=: read x y; echo "[$x][$y]"; }; printf "a::b\n" | { IFS=: read x y z; echo "[$x][$y][$z]"; }; printf " a : b \n" | { IFS=" :" read x y; echo "[$x][$y]"; }; printf "a b\n" | { IFS= read x; echo "[$x]"; }; printf ":a:\n" | { IFS=: read x y; echo "[$x][$y]"; }'
shf sh-read-more-fields-than-vars 'printf "a b c d\n" | { read x y; echo "[$y]"; }; printf "a:b:c:\n" | { IFS=: read x y; echo "[$y]"; }; printf "a  b  c  \n" | { read x y; echo "[$y]"; }'
shf sh-read-fewer-fields 'printf "a\n" | { read x y z; echo "[$x][$y][$z]"; }'
shf sh-read-from-file-fd 'printf "l1\nl2\nl3\n" > rf; exec 3< rf; read a <&3; read b <&3; echo "$a $b"; exec 3<&-; { read c; read d; } < rf; echo "$c $d"'
shf sh-read-shares-stdin-with-script 'printf "l1\nl2\n" | { read a; sh -c "read b; echo sub:\$b"; read c; echo "main:$a [$c]"; }'
same sh-read-errors "sh -c 'read 1x; echo after \$?' 2>/dev/null; sh -c 'read -z x; echo after \$?' 2>/dev/null; sh -c 'read x < /nonexist; echo after \$?' 2>/dev/null"
shf sh-read-loop-count 'seq 1 1000 > nums; n=0; while read x; do n=$((n+x)); done < nums; echo $n'
shf sh-true-false 'true; echo $?; false; echo $?; true x y; echo $?; false a; echo $?; if true && ! false; then echo both; fi'
shf sh-umask 'umask 022; umask; umask -S; umask u=rwx,g=,o=; umask; umask -S; umask 077; umask -S; umask a+r; umask; umask o-r; umask; umask 0; umask -S; umask g=w,o=x; umask; umask zz 2>/dev/null; echo st=$?; umask 022; : > um; ls -l um | cut -c1-10'
shf sh-unalias-alias-builtin-interplay 'alias x=echo 2>/dev/null; unalias x; alias x 2>/dev/null; echo st=$?'
shf sh-wait 'wait 12345 2>/dev/null; echo "st=$?"; wait; echo "st=$?"; sleep 0.1 & wait $!; echo "st=$?"; (exit 3) & wait $!; echo "st=$?"; (exit 4) & sleep 0.1; wait $!; echo "st=$?"; wait nope 2>/dev/null; echo st=$?'
shf sh-wait-multiple '(exit 1) & a=$!; (exit 2) & b=$!; wait $a; echo $?; wait $b; echo $?; wait $a; echo $?; true & false & wait; echo $?'
shf sh-wait-twice 'sleep 0.1 & p=$!; wait $p; echo $?; wait $p; echo $?'
shf sh-echo-builtin 'echo -n a; echo; echo -e x; echo "a\tb\\nc"; echo "\0101\0102"; echo a\\cb c; echo -n; echo -- x; echo -E y; echo - z; echo "\x41"; echo "\c"; echo x; echo -n -n y; echo'
shf sh-printf-builtin 'printf "%s %d %5.2f|%-3s|%03d|%x|%o|%c|%b|%%\n" a 42 3.14159 b 7 255 8 hi "x\ty"; printf "%s\n" a b c; printf "%d\n" "" 0x1f 010; printf "\101\x42\n"; printf "%5s|%-5s|\n" ab cd; printf "a\n" extra; echo st=$?; printf "%.3s\n" abcdef; printf "%d\n" abc 2>/dev/null; echo st=$?'
shf sh-test-builtin '[ -t 1 ]; echo $?; test -n ""; echo $?; [ 1 -eq 1 ] && echo eq; [ ]; echo $?; [ a = a -a b = b ]; echo $?; [ ! x ]; echo $?; [ -e /tmp ]; echo $?; test 1 -lt 2 -o 3 -lt 2; echo $?; [ -z "" -a -n a ]; echo $?; [ "(" = "(" ]; echo $?; [ 1 ]; echo $?; [ -f words.txt -a -d sub -a ! -d words.txt ]; echo $?; [ x 2>/dev/null; echo $?; test; echo $?'
shf sh-unsupported-builtins 'jobs 2>/dev/null; echo st=$?; bg 2>/dev/null; echo st=$?; fg 2>/dev/null; echo st=$?; local x 2>/dev/null; echo st=$?; ulimit 2>/dev/null; echo st=$?; echo continues'

# traps
shf sh-trap-exit 'trap "echo exiting \$?" EXIT; echo body; exit 3'
shf sh-trap-exit-normal-end 'trap "echo bye" EXIT; echo body; false'
shf sh-trap-exit-status-change 'trap "echo t; exit 9" EXIT; exit 2'
shf sh-trap-signals 'trap "echo usr" USR1; kill -USR1 $$; echo after; trap - USR1; trap "echo hup" HUP; kill -s HUP $$; kill -1 $$; echo done; trap "echo term" 15; kill -TERM $$; echo end'
shf sh-trap-ignore 'trap "" USR1; kill -USR1 $$; echo ignored; trap "" TERM; kill $$; echo still-here'
shf sh-trap-print 'trap "echo x" INT; trap "" TERM; trap "echo e" EXIT; trap; trap - INT; trap; trap x EXIT 0; trap | sed "s/x/y/"; trap -- "echo q" QUIT; trap | grep QUIT'
shf sh-trap-reset 'trap "echo nope" USR1; trap - USR1; kill -USR1 $$; echo not-reached' 
shf sh-trap-bad 'trap "echo bad" NOPE 2>/dev/null; echo st=$?; trap "echo k" KILL 2>/dev/null; echo st=$?; trap 2>/dev/null; echo end'
shf sh-trap-numbers 'trap "echo ten" 10; kill -10 $$; trap "echo zero" 0; trap | grep EXIT'
shf sh-trap-inherited-ignore 'trap "" USR1; sh -c "trap \"echo got\" USR1; kill -USR1 \$\$; echo after \$?"'
shf sh-trap-subshell-reset 'trap "echo parent-trap" USR1; (kill -USR1 $$); echo main; (trap "echo sub" USR1; kill -USR1 $$); (trap; echo sub-traps-cleared) | sed "s/.*//"'
shf sh-trap-wait 'trap "echo trapped" USR1; (sleep 0.3; kill -USR1 $$) & wait; echo "wait st=$?"; wait; echo done'
shf sh-trap-during-foreground 'trap "echo trapped" USR1; (sleep 0.3; kill -USR1 $$) & sleep 1; echo "sleep st=$?"'
shf sh-trap-status-preserved 'trap "true" USR1; (exit 5); kill -USR1 $$; echo $?; trap "false" USR2; (exit 6); kill -USR2 $$; echo $?'
shf sh-trap-exit-in-function 'f() { trap "echo from-trap" EXIT; }; f; echo body'
shf sh-trap-exit-not-in-cmdsub 'trap "echo exit-trap" EXIT; x=$(echo inner); echo $x'
shf sh-trap-exit-on-error 'trap "echo cleanup" EXIT; set -e; false; echo nope'
shf sh-trap-exit-on-fatal 'trap "echo cleanup2" EXIT; shift 5; echo nope'
shf sh-trap-with-args-exit 'trap "echo args: \$#" EXIT; set -- a b'
shf sh-trap-multiple-signals 'trap "echo caught" USR1 USR2; kill -USR1 $$; kill -USR2 $$; trap - USR1 USR2; kill -USR2 $$ 2>/dev/null; echo not-reached'
shf sh-trap-in-loop 'trap "echo T" USR1; for i in 1 2 3; do kill -USR1 $$; echo $i; done'
shf sh-trap-exit-in-loop-break 'trap "echo done" EXIT; for i in 1 2 3; do [ $i = 2 ] && break; echo $i; done'

# set -e
same sh-errexit-basic "sh -ec 'false; echo nope'; echo st=\$?; sh -ec 'if false; then :; fi; while false; do :; done; false || true; false && true; ! false; echo ok1'"
same sh-errexit-subshell "sh -ec '(false; echo nope); echo nope2'; echo st=\$?; sh -ec '(false; echo yes) || echo nope; echo ok2'"
same sh-errexit-function "sh -ec 'f() { false; echo inf; }; f || echo nope; echo ok3; f; echo nope'; echo st=\$?"
same sh-errexit-cmdsub "sh -ec 'x=\$(false); echo nope'; echo st=\$?; sh -ec 'echo \$(false); echo ok4'; sh -ec 'x=\$(false) || echo caught; echo ok'"
same sh-errexit-pipeline "sh -ec 'false | true; echo ok5; { false; echo nope; }'; echo st=\$?; sh -ec 'true | false; echo nope'; echo st=\$?"
same sh-errexit-if-body "sh -ec 'if true; then false; fi; echo nope'; echo st=\$?; sh -ec 'if false; then :; else false; fi; echo nope'; echo st=\$?"
same sh-errexit-loops "sh -ec 'until false; do break; done; echo ok6; set +e; false; echo ok7'; sh -ec 'for i in 1; do false; done; echo nope'; echo st=\$?; sh -ec 'while true; do false; done; echo nope'; echo st=\$?"
same sh-errexit-and-or "sh -ec 'nosuch 2>/dev/null || echo caught2; { false || true; } && echo ok8; ! true; echo ok9; false && echo a; echo ok10'; sh -ec 'true && false; echo nope'; echo st=\$?"
same sh-errexit-negation "sh -ec '! false; echo a; ! true; echo b'; echo st=\$?"
same sh-errexit-exit-status "sh -ec '(exit 7)'; echo st=\$?; sh -ec 'f() { return 9; }; f'; echo st=\$?; sh -ec 'false'; echo st=\$?"
same sh-errexit-set-later "sh -c 'false; echo a; set -e; false; echo nope'; echo st=\$?; sh -c 'set -e; set +e; false; echo b'"
same sh-errexit-while-cond-compound "sh -ec 'while ! false; do echo once; break; done; i=0; while [ \$i -lt 2 ]; do i=\$((i+1)); done; echo \$i'"
same sh-errexit-case "sh -ec 'case x in x) false;; esac; echo nope'; echo st=\$?; sh -ec 'case x in y) false;; esac; echo ok'"
same sh-errexit-brace-in-or "sh -ec '{ false; echo in; } || echo nope; echo ok'"
same sh-errexit-subshell-inherits-ignore "sh -ec '(false; echo a) && echo b; (exit 1) || echo c'"
same sh-errexit-trap-exit "sh -ec 'trap \"echo st=\\\$?\" EXIT; false'"
same sh-errexit-assignment-only "sh -ec 'x=1; echo ok'; sh -ec 'x=\$(exit 3); echo nope'; echo st=\$?"
same sh-errexit-redirect-error "sh -ec 'echo a > /nonexist/f; echo nope' 2>/dev/null; echo st=\$?"
same sh-errexit-not-found "sh -ec 'nosuchcmd; echo nope' 2>/dev/null; echo st=\$?"
same sh-errexit-eval "sh -ec 'eval false; echo nope'; echo st=\$?; sh -ec 'eval \"false || true\"; echo ok'"
same sh-errexit-dot "printf 'false\necho nope\n' > d.sh; sh -ec '. ./d.sh; echo nope2'; echo st=\$?"

# error reporting (stderr format pinned; dash says "sh: 1:", POSIX leaves the format open)
expect sh-error-not-found-msg 'a
sh: line 2: nosuch: not found
exit=127' "sh -c 'echo a
nosuch' 2>&1"
expect sh-error-syntax-msg 'sh: line 1: Syntax error: "fi" unexpected
exit=2' "sh -c 'echo a; fi' 2>&1"
expect sh-error-syntax-line 'line2
sh: line 3: Syntax error: end of file unexpected
exit=2' "sh -c '
echo line2
echo bad |' 2>&1"
expect sh-error-script-line 'a
sh: line 2: nosuch: not found
exit=0' "printf 'echo a\nnosuch\necho \$? > /dev/null\n' > e.sh; sh e.sh 2>&1"
expect sh-error-expansion-msg 'sh: line 1: x: parameter not set
exit=2' "sh -uc 'echo \$x' 2>&1"
expect sh-error-arith-msg 'sh: line 1: arithmetic expression: division by zero: "1/0"
exit=2' "sh -c 'echo \$((1/0))' 2>&1"
expect sh-error-redirect-msg 'sh: line 1: cannot open nosuch: No such file or directory
exit=2' "sh -c 'cat < nosuch' 2>&1"
expect sh-error-shift-msg "sh: line 1: shift: can't shift that many
exit=2" "sh -c 'shift 3' 2>&1"
expect sh-error-exec-msg 'sh: line 1: exec: nosuch: not found
exit=127' "sh -c 'exec nosuch' 2>&1 | sed 's/sh: line 1: nosuch/sh: line 1: exec: nosuch/'"
expect sh-error-i-unsupported 'sh: -i: interactive mode is not supported
exit=2' "sh -i -c 'echo i' 2>&1"
expect sh-error-m-unsupported 'sh: -m: job control is not supported
exit=2' "sh -m -c 'echo m' 2>&1"
expect sh-error-set-m 'sh: line 1: set: -m: job control is not supported
exit=2' "sh -c 'set -m; echo after' 2>&1"
expect sh-error-fallthrough-msg 'sh: line 1: Syntax error: "&" unexpected
exit=2' "sh -c 'case a in a) echo 1;& esac' 2>&1"
expect sh-error-jobs-msg 'sh: line 1: jobs: job control is not supported
after 2
exit=0' "sh -c 'jobs; echo after \$?' 2>&1"

# recorded choices where POSIX and dash disagree
shx sh-choice-stdin-shared 'got [hello world]
y=[]
exit=1' 'read x
echo "got [$x]"
hello world
read y
echo "y=[$y]"'
shx sh-choice-arith-recursive-var 'exit=2' 'y=1+1; echo $((y)) 2>/dev/null'
expect sh-choice-cd-cdpath-slash '/tmp
exit=0' "sh -c 'CDPATH=/ cd tmp'"

# other nebox applets from the shell
shf sh-applets-pipeline 'printf "b\na\nc\n" | sort | uniq | wc -l; seq 1 5 | awk "{ s += \$1 } END { print s }"; echo hello | tr a-z A-Z | rev; printf "x y\n" | cut -d" " -f2'
shf sh-applets-sed-awk-loop 'for w in alpha beta; do echo "$w" | sed "s/a/A/g"; done; awk "BEGIN { for (i = 1; i <= 3; i++) print i }" | while read n; do echo "n=$n"; done'
shf sh-applets-find-xargs 'find sub -type f | sort | xargs -n1 basename; ls sub | head -1; find . -name "*.txt" | wc -l'
shf sh-applets-test-expr 'if [ "$(expr 2 + 3)" -eq 5 ]; then echo five; fi; x=$(expr "abc" : "a\(.*\)"); echo $x; test -s words.txt && echo nonempty'
shf sh-applets-fs 'mkdir -p t/u; touch t/u/f; cp -r t t2; ls t2/u; mv t2 t3; [ -d t3 ] && echo moved; rm -r t3; [ ! -e t3 ] && echo gone; ln -s words.txt wl; readlink wl; cat wl | head -1'
shf sh-applets-cksum-loop 'for f in words.txt nums.txt; do printf "%s " "$f"; cksum < "$f" | cut -d" " -f1; done | sort'
shf sh-applets-env-vars 'FOO=bar env | grep "^FOO="; export BAZ=1; printenv BAZ; env -i PATH="$PATH" sh -c "echo \${BAZ:-unset}"'
shf sh-applets-xargs-sh 'printf "1\n2\n3\n" | xargs -n1 sh -c "echo arg:\$0"; printf "a b\n" | xargs sh -c "echo \$# \$1 \$2" x'
shf sh-applets-sh-nested 'sh -c "sh -c \"sh -c \\\"echo deep \\\$((1+1))\\\"\""; echo $(sh -c "echo \$(sh -c \"echo inner\")")'
shf sh-applets-dd-head 'head -c 100 big.bin | wc -c; dd if=big.bin bs=1000 count=2 2>/dev/null | wc -c; printf "abc" | od -c | head -1'
shf sh-applets-timeout 'timeout 5 sh -c "exit 3"; echo $?; timeout 1 sh -c "sleep 5"; echo $?'
shf sh-applets-script-file 'cat > prog.sh <<EOF
#!/bin/sh
total=0
for n in "\$@"; do total=\$((total + n)); done
echo "sum=\$total"
EOF
chmod +x prog.sh; ./prog.sh 1 2 3; sh prog.sh 4 5'

#!/bin/sh
# nebox conformance tests. Each `same` case runs one shell command twice from
# identical fixture directories: once with the host's own utilities, once with
# nebox's applet links first on PATH. stdout, exit status, and the resulting
# directory tree must match. The driver is the host's /bin/sh explicitly, so
# nebox's own sh applet is exercised only where a case invokes `sh`. `expect` cases pin an exact output where the host
# reference is not comparable.
set -u
BIN=$(CDPATH= cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")
W=$(mktemp -d "${TMPDIR:-/tmp}/nebox-test.XXXXXX")
trap 'rm -rf "$W"' EXIT HUP INT TERM
pass=0; fail=0; failed=""

"$BIN" --install -s "$W/bin" || { echo "install failed"; exit 1; }

mkdir -p "$W/fixture/sub/deep" "$W/fixture/empty"
printf 'alpha\nbeta\ngamma\ndelta\nalpha\n' > "$W/fixture/words.txt"
printf '10\n9\n100\n-3\n2.5\n' > "$W/fixture/nums.txt"
printf 'one two  three\n\nfour\tfive\nsix\n' > "$W/fixture/spaces.txt"
printf 'no trailing newline' > "$W/fixture/nonl.txt"
printf 'a:b:c\nd:e:f\nnodelim\n' > "$W/fixture/fields.txt"
printf 'Apple\nbanana\napple\nBanana\ncherry\n' > "$W/fixture/case.txt"
head -c 200000 /dev/urandom > "$W/fixture/big.bin"
printf 'deep file\n' > "$W/fixture/sub/deep/file"
ln -s words.txt "$W/fixture/link"
: > "$W/fixture/zero"
chmod 640 "$W/fixture/zero"

snapshot() {
  (cd "$1" && find . -mindepth 1 | LC_ALL=C sort | while read -r p; do
    if [ -L "$p" ]; then printf 'L %s -> %s\n' "$p" "$(readlink "$p")"
    elif [ -d "$p" ]; then printf 'D %s %s\n' "$p" "$(stat -c %a "$p")"
    else printf 'F %s %s %s\n' "$p" "$(stat -c %a "$p")" "$(cksum < "$p")"; fi
  done)
}

run_in() { # dir path-prefix command
  rm -rf "$1"; cp -a "$W/fixture" "$1"
  (cd "$1" && LC_ALL=C PATH="$2$PATH" timeout 20 /bin/sh -c "$3" 2>"$1.err"; echo "exit=$?") > "$1.out"
}

# Reference implementations that are not the host's default go in $W/refbin
# (tests/awk.sh puts a `gawk --posix` wrapper there); REFPATH prefixes the
# reference run's PATH.
REFPATH=""

same() { # name command
  name=$1; cmd=$2
  run_in "$W/ref" "$REFPATH" "$cmd"
  run_in "$W/got" "$W/bin:" "$cmd"
  if cmp -s "$W/ref.out" "$W/got.out" && [ "$(snapshot "$W/ref")" = "$(snapshot "$W/got")" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1)); failed="$failed $name"
    echo "FAIL $name: $cmd"
    diff -u "$W/ref.out" "$W/got.out" | sed 's/^/  /' | head -20
    snapshot "$W/ref" > "$W/ref.snap"; snapshot "$W/got" > "$W/got.snap"
    diff -u "$W/ref.snap" "$W/got.snap" | sed 's/^/  /' | head -20
    [ -s "$W/got.err" ] && sed 's/^/  stderr: /' "$W/got.err" | head -5
  fi
}

expect() { # name expected-stdout command
  name=$1; want=$2; cmd=$3
  run_in "$W/got" "$W/bin:" "$cmd"
  got=$(cat "$W/got.out")
  if [ "$got" = "$want" ]; then pass=$((pass+1)); else
    fail=$((fail+1)); failed="$failed $name"
    printf 'FAIL %s: %s\n  want: %s\n  got:  %s\n' "$name" "$cmd" "$want" "$got"
    [ -s "$W/got.err" ] && sed 's/^/  stderr: /' "$W/got.err" | head -5
  fi
}

# echo / printf
same echo-plain 'echo hello world'
same echo-n 'echo -n hi; echo'
same echo-e 'echo -e "a\tb\nc\\\\d"'
same echo-empty 'echo'
same printf-basic 'printf "%s=%d\n" x 42 y 7'
same printf-width 'printf "[%5s][%-5s][%05d][%x][%o][%c]\n" ab cd 42 255 8 hello'
same printf-escape 'printf "a\tb\\\\n\n"'
same printf-percent 'printf "100%%\n"'
same printf-float 'printf "%e|%g|%.1f|%E|%G|%F|%08.3f|%-8.2e|\n" 12345.678 0.0001 2.25 1.5 2e10 3 3.14159 -42; printf "%f\n" 1x; echo st=$?'
same printf-b 'printf "%b|%5b|%-4b|\n" "a\tb\0101" x y; printf "%b\n" "x\cy" z; echo after'
# cat / head / tail
same cat-file 'cat words.txt'
same cat-stdin 'cat < words.txt'
same cat-multi 'cat words.txt nonl.txt words.txt'
same cat-n 'cat -n spaces.txt'
same cat-b 'cat -b spaces.txt'
same cat-missing 'cat nope.txt'
same cat-big 'cat big.bin | cksum'
same head-default 'seq 1 20 | head'
same head-n 'head -n 2 words.txt'
same head-legacy 'head -3 words.txt'
same head-neg 'head -n -2 words.txt'
same head-c 'head -c 7 words.txt'
same head-multi 'head -n 1 words.txt nums.txt'
same tail-default 'seq 1 20 | tail'
same tail-n 'tail -n 2 words.txt'
same tail-plus 'tail -n +3 words.txt'
same tail-c 'tail -c 6 words.txt'
same tail-nonl 'tail -n 1 nonl.txt'
same tail-multi 'tail -n 1 words.txt nums.txt'
# wc
same wc-default 'wc words.txt'
same wc-l 'wc -l < words.txt'
same wc-multi 'wc -l -w words.txt spaces.txt nonl.txt'
same wc-c 'wc -c big.bin'
same wc-L 'wc -L spaces.txt'
# sort / uniq
same sort-plain 'sort words.txt'
same sort-r 'sort -r words.txt'
same sort-n 'sort -n nums.txt'
same sort-nr 'sort -nr nums.txt'
same sort-u 'sort -u words.txt'
same sort-f 'sort -f case.txt'
same sort-o 'sort -o out.txt words.txt; cat out.txt'
same sort-stdin 'printf "b\na\n" | sort'
same sort-k2 'printf "x b z\ny b a\nz a q\n" | sort -k2'
same sort-k2-2 'printf "x b z\ny b a\nz a q\n" | sort -k2,2'
same sort-k-n 'printf "a 10\nb 9\nc 100\nd -1\n" | sort -k2n; printf "a 10\nb 9\nc 100\n" | sort -k2,2n'
same sort-k-r 'printf "a 2\nb 1\nc 1\n" | sort -k2,2r; printf "a 2\nb 1\nc 1\n" | sort -r -k2,2'
same sort-k-multi 'printf "a 2 x\nb 1 y\na 1 z\nb 10 w\n" | sort -k1,1 -k2n; printf "a 2 x\nb 1 y\na 1 z\n" | sort -k2,2n -k1,1r'
same sort-k-char 'printf "abc\nabd\naba\nab\n" | sort -k1.3,1.3; printf "xa12\nxb3\nxc7\n" | sort -k1.3n'
same sort-k-inherit 'printf "1 b\n2 a\n10 c\n" | sort -n -k2r; printf "1 b\n2 a\n10 c\n" | sort -n -k2; printf "1 b\n2 a\n10 c\n" | sort -n -k1,1 -k2'
same sort-t 'sort -t: -k2 fields.txt; sort -t: -k3,3 fields.txt; sort -t: -k1,1 fields.txt; printf "a:bc:zz\na:bd:aa\na:bc:yy\n" | sort -t: -k2,2.10'
same sort-t-nul 'printf "a\0b\nc\0a\n" | sort -t "\\0" -k2 | tr "\0" "_"'
same sort-t-bad 'sort -t ab words.txt; echo $?; sort -t "" words.txt; echo $?'
same sort-b 'printf "  b\n a\nc\n" | sort -b; printf "  b\n a\nc\n" | sort; printf "x  b\nx a\n" | sort -b -k2; printf "x  b\nx a\n" | sort -k2'
same sort-k-b 'printf "x   b\nx  a\n" | sort -k2b; printf "x  b\nx a\n" | sort -k2,2.1b; printf "x  b\nx a\n" | sort -k2,2.1'
same sort-s 'printf "b 1\na 1\nc 0\n" | sort -s -k2,2; printf "b 1\na 1\nc 0\n" | sort -k2,2; printf "b\na\n" | sort -s'
same sort-c 'sort -c words.txt; echo $?; sort words.txt > s; sort -c s; echo $?; printf "a 1\nb 2\n" | sort -c -k2n; echo $?; : > e; sort -c e; echo $?'
same sort-C 'sort -C words.txt; echo $?; seq 3 | sort -C; echo $?'
same sort-cu 'printf "a\na\n" | sort -cu; echo $?; printf "a\nb\n" | sort -cu; echo $?; printf "a 1\nb 1\n" | sort -cu -k2,2; echo $?'
same sort-c-bad 'sort -c -o x words.txt; echo $?; sort -c words.txt nums.txt; echo $?'
same sort-d 'printf "a-c\nab\na c\nA_b\n" | sort -d; printf "x a-c\ny ab\n" | sort -k2d'
same sort-i 'printf "a\001c\nab\n" | sort -i | od -c; printf "x a\001c\ny ab\n" | sort -k2i | od -c; printf "a\001c\nab\n" | sort -di | od -c'
same sort-m 'printf "a\nc\ne\n" > a; printf "b\nd\n" > b; sort -m a b; printf "a\nc\nb\n" > a; sort -m a b; printf "2\n10\n" > a; printf "3\n" > b; sort -mn a b; sort -mnr a b'
same sort-mu 'printf "a\nb\nb\n" > a; printf "b\nd\n" > b; sort -mu a b; printf "a 1\nb 2\n" > a; printf "c 1\n" > b; sort -mu -k2,2 a b; sort -m -s -k2,2 a b'
same sort-z 'printf "b\0a\0" | sort -z | tr "\0" "\n"; printf "b\na\0a\0" | sort -z | od -c; printf "b\0a" | sort -z | od -c; printf "x 2\0y 1\0" | sort -z -k2n | tr "\0" "\n"'
same sort-V 'printf "a.txt\na01.txt\na1.tar.gz\n.hidden\n..\n.\nfoo~\nfoo\nfoo1\nfoo01\nfoo-1\nfoo_1\nFoo\n1.10\n1.9\n1.9.1\nabc.d1e\n\n2a\n10a\n" | sort -V; printf "x 1.10\ny 1.9\n" | sort -k2V'
same sort-h 'printf "1K\n1k\n2000\n1M\n1.5K\n-1K\n0\n1Ki\n1T\n1E\n1Z\n1Y\n1P\n1G\n3\n0K\nabc\n-2M\n" | sort -h; printf "x 1K\ny 900\n" | sort -k2h'
same sort-hr 'printf "1K\n2000\n1M\n" | sort -hr; printf "1K\n2000\n1M\n" | sort -h -u'
same sort-u-key 'printf "01 x\n1 y\n2 z\n" | sort -nu; printf "01 x\n1 y\n" | sort -n -k1,1 -u; printf "a 1\nb 1\nc 2\n" | sort -u -k2,2; printf "a 1\nb 1\n" | sort -u -s -k2,2'
same sort-fu 'sort -fu case.txt; printf "_\na\nA\n[\n" | sort -f; printf "x _\ny a\n" | sort -k2f'
same sort-n-edge 'printf "+5\n3\nabc\n-2\n0\n 7\n-0\n.5\n1e3\n-.5\n0.50\n00\n-\n" | sort -n; printf "12345678901234567890\n2345678901234567890\n12345678901234567891\n" | sort -n'
same sort-o-input 'sort -o words.txt words.txt; cat words.txt; sort -n -o nums.txt nums.txt; cat nums.txt'
same sort-empty ': > e; sort e | wc -c; sort < e | wc -c; sort -u e | wc -c'
same sort-nonl 'sort nonl.txt | od -c; printf "b\na" | sort | od -c; printf "b\na" | sort -o out; od -c out'
same sort-multi 'sort words.txt case.txt nums.txt; sort -u words.txt words.txt'
same sort-dash 'cat words.txt | sort - nums.txt; cat case.txt | sort words.txt -'
same sort-missing 'sort words.txt nope.txt; echo $?; sort -c nope.txt; echo $?'
same sort-k-bad 'sort -k0 words.txt; echo $?; sort -k1x words.txt; echo $?; sort -k1.0 words.txt; echo $?; sort -k1,0 words.txt; echo $?; sort -k words.txt; echo $?; sort -kx words.txt; echo $?'
same sort-incompat 'sort -nV words.txt; echo $?; sort -k1nh words.txt; echo $?'
same uniq-plain 'sort words.txt | uniq'
same uniq-c 'sort words.txt | uniq -c'
same uniq-d 'sort words.txt | uniq -d'
same uniq-u 'sort words.txt | uniq -u'
same uniq-i 'printf "a\nA\nb\n" | uniq -i'
# grep (fixed strings)
same grep-plain 'grep alpha words.txt'
same grep-i 'grep -i APPLE case.txt'
same grep-v 'grep -v a words.txt'
same grep-n 'grep -n a words.txt'
same grep-c 'grep -c a words.txt'
same grep-l 'grep -l alpha words.txt nums.txt case.txt'
same grep-multi 'grep a words.txt case.txt'
same grep-h 'grep -h a words.txt case.txt'
same grep-q 'grep -q zzz words.txt; echo $?'
same grep-w 'printf "cat\ncatalog\nthe cat sat\n" | grep -w cat'
same grep-x 'grep -x beta words.txt'
same grep-nomatch 'grep zzz words.txt; echo $?'
same grep-F 'printf "a.c\nabc\n" | grep -F a.c'
# tr / cut / rev / nl
same tr-upper 'echo hello | tr a-z A-Z'
same tr-d 'echo hello world | tr -d lo'
same tr-s 'echo "aaabbbccc  d" | tr -s "abc "'
same tr-c 'echo "ab1cd2" | tr -c 0-9 x'
same tr-esc 'printf "a b\n" | tr " " "\\n"'
same cut-f 'cut -d: -f2 fields.txt'
same cut-f-range 'cut -d: -f1,3 fields.txt'
same cut-f-open 'cut -d: -f2- fields.txt'
same cut-s 'cut -d: -s -f1 fields.txt'
same cut-c 'cut -c2-4 words.txt'
same cut-c-list 'cut -c1,5 words.txt'
same rev-plain 'rev words.txt'
same rev-nonl 'rev nonl.txt'
same nl-default 'nl spaces.txt'
same nl-ba 'nl -ba spaces.txt'
# seq / yes
same seq-1 'seq 5'
same seq-2 'seq 3 6'
same seq-3 'seq 10 -3 1'
same seq-w 'seq -w 8 12'
same seq-s 'seq -s, 1 4'
same seq-neg 'seq -2 2'
same yes-head 'yes | head -n 3'
same yes-arg 'yes hello | head -n 2'
# tee
same tee-plain 'echo data | tee t1.txt t2.txt'
same tee-a 'echo one > t.txt; echo two | tee -a t.txt; cat t.txt'
# paths
same basename-1 'basename /usr/lib/libc.so.6'
same basename-suffix 'basename /a/b/file.txt .txt'
same basename-slash 'basename /a/b/'
same basename-root 'basename /'
same basename-a 'basename -a /x/y /z'
same basename-s 'basename -s .c a.c b.c'
same dirname-1 'dirname /usr/lib/libc.so.6'
same dirname-2 'dirname file'
same dirname-3 'dirname /a/b/'
same dirname-4 'dirname /'
same dirname-5 'dirname a/b'
same dirname-multi 'dirname /a/b /c'
same pwd-plain 'cd sub && pwd | sed "s|.*/||"'
same readlink-1 'readlink link'
same readlink-f 'readlink -f link | sed "s|.*/||"'
same readlink-fail 'readlink words.txt; echo $?'
# ls
same ls-1 'ls -1'
same ls-a 'ls -a sub'
same ls-sub 'ls sub'
same ls-d 'ls -d sub'
same ls-multi 'ls -1 sub empty'
same ls-R 'ls -R sub'
same ls-F 'ls -F'
same ls-missing 'ls nope; echo $?'
same ls-file 'ls words.txt'
# mkdir / rmdir / rm / touch
same mkdir-1 'mkdir newdir'
same mkdir-p 'mkdir -p a/b/c/d'
same mkdir-m 'mkdir -m 700 secret'
same mkdir-exists 'mkdir sub; echo $?'
same rmdir-1 'rmdir empty'
same rmdir-p 'mkdir -p x/y/z && rmdir -p x/y/z'
same rmdir-notempty 'rmdir sub; echo $?'
same rm-1 'rm words.txt'
same rm-r 'rm -r sub'
same rm-f 'rm -f nope; echo $?'
same rm-missing 'rm nope; echo $?'
same rm-dir 'rm sub; echo $?'
same rm-link 'rm link'
same touch-new 'touch newfile; ls newfile'
same touch-c 'touch -c nope; ls'
# cp / mv / ln
same cp-1 'cp words.txt copy.txt'
same cp-into 'cp words.txt sub; ls sub'
same cp-r 'cp -r sub clone'
same cp-multi 'cp words.txt nums.txt empty'
same cp-p 'cp -p zero zero2'
same cp-dir-nor 'cp sub x; echo $?'
same cp-missing 'cp nope x; echo $?'
same mv-1 'mv words.txt moved.txt'
same mv-into 'mv words.txt sub'
same mv-dir 'mv sub renamed'
same mv-missing 'mv nope x; echo $?'
same ln-s 'ln -s words.txt sl'
same ln-hard 'ln words.txt hl'
same ln-into 'ln -s ../words.txt sub'
same ln-f 'ln -sf nums.txt link'
# chmod
same chmod-octal 'chmod 600 words.txt'
same chmod-plus 'chmod +x words.txt'
same chmod-ugo 'chmod u-w,go+w words.txt'
same chmod-eq 'chmod o=r words.txt'
same chmod-R 'chmod -R g-r sub'
same chmod-missing 'chmod 644 nope; echo $?'
# test / [
same test-e 'test -e words.txt; echo $?'
same test-f 'test -f sub; echo $?'
same test-d '[ -d sub ]; echo $?'
same test-s 'test -s zero; echo $?'
same test-L 'test -L link; echo $?'
same test-z 'test -z ""; echo $?'
same test-n 'test -n ""; echo $?'
same test-eq 'test 3 -eq 3; echo $?'
same test-lt 'test 3 -lt 2; echo $?'
same test-str '[ abc = abc ]; echo $?'
same test-ne '[ abc != abc ]; echo $?'
same test-not '[ ! -e nope ]; echo $?'
same test-a '[ -e words.txt -a -d sub ]; echo $?'
same test-o '[ -e nope -o -d sub ]; echo $?'
same test-empty 'test; echo $?'
same test-one 'test x; echo $?'
same test-bad-int 'test a -eq 1; echo $?'
# env / printenv / which / true / false / id / uname / hostname / nproc
same true 'true; echo $?'
same false 'false; echo $?'
same env-var 'env FOO=bar sh -c "echo \$FOO"'
same env-list 'env -i A=1 B=2 env | sort'
same env-u 'FOO=1 env -u FOO sh -c "echo [\$FOO]"'
same printenv-1 'FOO=bar printenv FOO'
same printenv-missing 'printenv NEBOX_NOPE; echo $?'
same which-sh 'which sh | sed "s,.*/,,"'
same which-missing 'which nebox-nope-cmd; echo $?'
same id-u 'id -u'
same id-g 'id -g'
same uname-s 'uname -s'
same uname-m 'uname -m'
same uname-r 'uname -r'
same uname-n 'uname -n'
same hostname 'hostname'
same nproc 'nproc'
same sleep-0 'sleep 0.1; echo done'
same kill-0 'kill -0 $$; echo $?'
same kill-l 'kill -l TERM >/dev/null; echo $?'
same date-r 'date -u -r words.txt +%Y-%m-%d'
same date-d 'date -u -d @0 "+%Y %H:%M"'
# dispatch
expect list-has-cat 'exit=0' "$BIN --list | grep -qx cat"
expect unknown-applet 'exit=127' "$BIN nosuchapplet"
expect multicall 'ok
exit=0' "$BIN echo ok"
expect nosuch-link 'hi
exit=0' "cp $W/bin/cat ./nosuch 2>/dev/null; ./nosuch echo hi"
same tail-plus-c 'tail -c +4 words.txt'
same tr-s-one 'echo "aaabbb" | tr -s ab'
same printf-noconv 'printf "hi\n" a b'
same ls-l-dir 'ls -l sub | sed "s/[A-Z][a-z][a-z] *[0-9]* [0-9:]*//"'
same ls-l-total 'ls -l empty' 
same ls-l-file 'ls -l words.txt | sed "s/[A-Z][a-z][a-z] *[0-9]* [0-9:]*//"'
same ls-l-all 'ls -la | sed "s/[A-Z][a-z][a-z] *[0-9]* [0-9:]*//"'
same id-full 'id'
same id-G 'id -G; id -Gn'
same id-un 'id -un'
same id-gn 'id -gn'
same head-pipe 'yes | head -c 5'
same wc-stdin-all 'wc < words.txt'
same wc-pipe 'cat words.txt | wc'
same wc-two 'wc words.txt big.bin'
same nl-s 'nl -s: -w3 spaces.txt'
same seq-opt-bad 'seq -x 3; echo $?' 
expect grep-E-works 'exit=0' "grep -E a words.txt >/dev/null"


# regex grep
same grep-bre 'grep "a.pha" words.txt'
same grep-bre-star 'grep "^al*" words.txt'
same grep-bre-anchor 'grep "a$" words.txt'
same grep-bre-group 'grep "\(al\|be\)" words.txt'
same grep-bre-interval 'grep "p\{2\}" case.txt'
same grep-E-alt 'grep -E "alpha|gamma" words.txt'
same grep-E-plus 'grep -E "p+le" case.txt'
same grep-E-class 'grep -E "^[[:upper:]]" case.txt'
same grep-E-neg 'grep -E "^[^abc]" words.txt'
same grep-E-count 'grep -Ec "a" words.txt case.txt'
same grep-E-i 'grep -Ei "^apple$" case.txt'
same grep-E-w 'grep -Ew "two|five" spaces.txt'
same grep-E-x 'grep -Ex "al.*" words.txt'
same grep-E-o 'grep -Eo "[a-z]+a" words.txt'
same grep-E-on 'grep -Eon "[0-9]+" nums.txt'
same grep-E-bad 'grep -E "(" words.txt; echo $?'
same grep-E-backref 'echo "abab abcd" | grep -Eo "(ab)\\1"'
same grep-E-m 'grep -Em 2 "a" words.txt'
same grep-E-r 'grep -Er "deep" sub | sort'
same grep-E-v 'grep -Ev "a" words.txt'
same grep-E-empty 'grep -E "" nonl.txt'
same grep-E-brace-literal 'echo "a{b" | grep -E "a{b"'
same grep-w-regex 'grep -w "fiv." spaces.txt; echo $?'
same grep-two-e 'grep -e alpha -e beta words.txt'
# regex leftmost-longest (GNU grep/sed/expr semantics; src/nebox/regex.nelua)
same re-alt-prefix-o 'echo abcd | grep -oE "ab|abc"'
same re-alt-prefix-ladder 'echo abcd | grep -oE "a|ab|abc|abcd"; echo "xyz xy x" | grep -oE "x|xy|xyz"'
same re-alt-prefix-mid 'echo abcabc | grep -oE "abc|a|ab"; echo foobar | grep -oE "foo|foobar"'
same re-alt-prefix-i 'echo ABCD | grep -ioE "ab|abc"'
same re-alt-prefix-bre 'echo abcd | grep -o "ab\|abc"'
same re-alt-groups 'echo abcd | sed -E "s/(a|ab)(c|bcd)(d*)/[\1][\2][\3]/"'
same re-alt-groups-anchored 'echo abcd | sed -E "s/(a|ab)(c|bcd)(d*)$/[\1][\2][\3]/"'
same re-alt-groups-two 'echo aaa | sed -E "s/(a|aa)(a|aa)/[\1][\2]/"; echo xyz | sed -E "s/(x|xy)(z|yz)/[\1][\2]/"'
same re-alt-groups-opt 'echo abab | sed -E "s/(ab|a)(bab)?/[\1][\2]/"; echo xyxyxyz | sed -E "s/(xy)*(xyz)?/[\1][\2]/"'
same re-alt-either 'echo ab | sed -E "s/(a)|(b)/[\1][\2]/g"; echo aXbXc | sed -E "s/(X|Xb)/[\1]/g"'
same re-star-group-empty 'echo b | sed -E "s/(a*)*/[\1]/"; echo b | sed -E "s/(a*)+/[\1]/"'
same re-star-group-full 'echo aaa | sed -E "s/(a*)*/[\1]/"; echo aaa | sed -E "s/(a*)+/[\1]/"; expr aaa : "\(a*\)*"'
same re-star-group-last 'echo aaa | sed -E "s/(a|aa)*/[\1]/"; echo abba | sed -E "s/(a|b|ab|ba)*/[\1]/"; echo aa | sed -E "s/(a?)*/[\1]/"'
same re-star-group-nested 'echo abc | sed -E "s/(a(b)?)+/[\1][\2]/"; echo aba | sed -E "s/(a(b)?)+/[\1][\2]/"'
same re-star-group-greedy 'echo zzz | sed -E "s/(z)*(z*)/[\1][\2]/"; echo ab | sed -E "s/(a*)(ab)*(b*)/[\1][\2][\3]/"; echo aab | sed -E "s/(a*)(ab)*(b*)/[\1][\2][\3]/"'
same re-star-group-interval 'echo aaa | sed -E "s/(a{1,2})*/[\1]/"; echo aba | sed -E "s/(a|b){2}/[\1]/"'
same re-star-unused-group 'echo ac | sed "s/a\(b\)*c/[\1]/"; echo abc | sed "s/\(b\)*c/[\1]/"'
same re-empty-branch 'echo xaax | sed -E "s/(a|)+/[\1]/g"; echo abab | sed -E "s/(|a)*/[\1]/"; echo abab | grep -oE "(|ab)*"'
same re-empty-branch-top 'echo abc | sed -E "s/a||b/X/g"; echo abc | grep -E "a||b"; echo abc | grep -oE "(a|)"'
same re-empty-match-o 'echo abc | grep -oE "x*"; echo $?; echo abc | grep -E "x*"; echo $?; echo abc | grep -oE "()"; echo $?'
same re-wordb-longest 'echo "abc abd" | sed -E "s/\<(ab|abc)\>/[\1]/g"; echo "the cat" | sed -E "s/\b(c|ca)t?/[\1]/g"'
same re-backref-longest 'echo abcabc | sed "s/\(.*\)\1/[\1]/"; echo abcabcx | sed "s/\(.*\)\1/[\1]/"; echo aaaa | sed -E "s/(a*)\1/[\1]/"'
same re-backref-expr 'expr xabcabcx : "x\(.*\)\1"; expr aaa : "\(a*\)\1"'
same re-backref-alt 'echo abab | sed -E "s/(a|ab)(ab|b)\1/[\1][\2]/"; echo abcabcabc | sed -E "s/(abc)*\1/[\1]/"; echo xx | sed -E "s/(x)\1*/[\1]/"'
same re-backref-o 'echo "aa aaa" | grep -oE "(a*)\1"; echo aaaaaaaa | grep -oE "(a|aa)*\1a"; echo Abab | grep -ioE "(ab)\1"'
same re-backref-unset 'echo ac | grep -E "a(b)?\1c"; echo $?; echo ac | grep -E "a(b)*\1c"; echo $?; echo abbc | sed -E "s/a(b)*\1c/[\1]/"'
same re-expr-longest 'expr abcd : "ab\|abc"; expr abcd : "\(ab\|abc\)"; expr xyz : "x\(y\|yz\)"; expr xyz : "\(x\|xy\)\(z\|yz\)"'
same re-sed-g-empty 'echo abc | sed "s/x*/-/g"; echo abc | sed -E "s/b*/-/g"; echo baaac | sed -E "s/a*/-/g"; echo hello | sed "s/l*/X/g"'
same re-sed-g-empty-groups 'echo abc | sed -E "s/(a|ab)*/[&]/g"; echo aXbXc | sed "s/b*/-/g"'
same re-sed-n-empty 'echo baaac | sed -E "s/a*/-/2"; echo baaac | sed -E "s/a*/-/3"; echo baaac | sed -E "s/a*/-/3g"; echo abc | sed -E "s/x*/-/2"'
same re-pathological 'A=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; echo $A | grep -cE "(a|aa)*b"; echo $?; echo ${A}b | grep -oE "(a|aa)*b"; echo $A$A$A | grep -cE "(a|aa)*b"; echo $A | sed -E "s/(a|aa)*b/X/"'
same re-pathological-backref 'A=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; echo $A | grep -cE "(a|aa)*\1b"; echo $?; echo $A | grep -cE "(a|aa)*\1a"'
# GNU grep does not finish this one within the harness timeout; nebox stops at
# its thread bound and reports "pattern too complex" (exit 2).
expect re-too-complex 'exit=2' 'head -c 400 /dev/zero | tr "\\0" a | grep -cE "(.*)(.*)(.*)\3\2\1" 2>/dev/null'
expect re-too-complex-sed 'exit=4' 'head -c 400 /dev/zero | tr "\\0" a | sed -E "s/(.*)(.*)(.*)\3\2\1/X/" 2>/dev/null'
# Equivalence classes are not implemented: "[[=a=]]" parses as the set {[ = a}
# followed by a literal "]", so this does not match where GNU grep would.
expect re-equiv-unsupported 'exit=1' 'echo a | grep "[[=a=]]"'
expect re-too-complex-expr 'exit=2' 'expr "$(head -c 400 /dev/zero | tr "\\0" a)" : "\(.*\)\(.*\)\(.*\)\3\2\1" 2>/dev/null'
# cmp / comm / tac
same cmp-same 'cmp words.txt words.txt; echo $?'
same cmp-diff 'cmp words.txt case.txt; echo $?'
same cmp-eof 'cmp words.txt link; printf "x" >> link2; cat words.txt >> link2; cmp words.txt link2; echo $?'
same cmp-s 'cmp -s words.txt nums.txt; echo $?'
same cmp-l 'cmp -l words.txt case.txt | head -3; echo $?'
same comm-basic 'sort words.txt > a; sort case.txt > b; comm a b'
same comm-12 'sort words.txt > a; sort words.txt > b; comm -12 a b'
same comm-3 'sort words.txt > a; sort case.txt > b; comm -3 a b'
same tac-basic 'tac words.txt'
same tac-nonl 'tac nonl.txt words.txt'
# fold / paste / expand / unexpand
same fold-w 'fold -w 5 words.txt'
same fold-s 'fold -s -w 8 spaces.txt'
same fold-tab 'printf "a\tb\tc\td\n" | fold -w 10'
same paste-two 'paste words.txt nums.txt'
same paste-d 'paste -d, words.txt nums.txt case.txt'
same paste-s 'paste -s words.txt'
same paste-sd 'paste -s -d "+-" nums.txt'
same expand-default 'expand spaces.txt'
same expand-t4 'expand -t 4 spaces.txt'
same expand-list 'printf "\ta\tb\tc\n" | expand -t 3,6,12'
same unexpand-leading 'printf "        a  b\n    c\n" | unexpand'
same unexpand-a 'printf "a        b        c\n" | unexpand -a'
same unexpand-t4 'printf "    x\n        y\n" | unexpand -t 4'
# checksums
same cksum-file 'cksum words.txt nums.txt'
same cksum-stdin 'cksum < big.bin'
same md5-file 'md5sum words.txt big.bin'
same md5-stdin 'md5sum < nonl.txt'
same sha1-file 'sha1sum words.txt big.bin'
same sha256-file 'sha256sum words.txt big.bin nonl.txt'
same sha256-empty 'sha256sum zero'
same md5-check 'md5sum words.txt nums.txt > sums; md5sum -c sums; echo $?'
same sha256-check-bad 'sha256sum words.txt > sums; echo x >> words.txt; sha256sum -c sums 2>/dev/null; echo $?'
# base64 / strings / split
same base64-enc 'base64 words.txt'
same base64-wrap 'base64 -w 0 big.bin; echo'
same base64-big 'base64 big.bin'
same base64-dec 'base64 words.txt | base64 -d'
same base64-roundtrip 'base64 big.bin | base64 -d | cksum'
same base64-w10 'base64 -w 10 words.txt'
same strings-min 'strings -n 3 big.bin | head -5; echo'
same strings-text 'strings words.txt'
same split-l 'split -l 2 words.txt part.; cat part.aa part.ab part.ac'
same split-b 'split -b 70000 big.bin; ls'
same split-d 'split -d -l 1 nums.txt n; ls'
same split-a 'split -a 3 -l 3 words.txt; ls'
# du / stat
same du-s 'du -s sub'
same du-a 'du -a sub | sort'
same du-b 'du -b words.txt nums.txt'
same du-sh 'du -sh sub'
same du-c 'du -c words.txt nums.txt'
same du-k 'du -k . | sort'
same stat-c 'stat -c "%n %s %F %a" words.txt sub zero'
same stat-link 'stat -c "%N %F" link'
same stat-L 'stat -L -c "%n %s %F" link'
same stat-u 'stat -c "%u %g %U %G %h" words.txt'
same stat-missing 'stat -c %n nosuch; echo $?'
# chown / chgrp
same chown-self 'chown $(id -u) words.txt; echo $?'
same chown-name 'chown $(id -un):$(id -gn) words.txt; echo $?'
same chgrp-self 'chgrp $(id -g) words.txt; echo $?'
same chown-R 'chown -R $(id -u) sub; echo $?'
same chown-bad-user 'chown nosuchuser words.txt 2>/dev/null; echo $?'
# mktemp / truncate / realpath / link / unlink
same mktemp-u 'f=$(mktemp -u -p . foo.XXXXXX); case "$f" in ./foo.??????) echo ok;; *) echo "$f";; esac'
same mktemp-file 'f=$(mktemp -p .); test -f "$f" && echo yes; rm "$f"'
same mktemp-dir 'd=$(mktemp -d -p . dir.XXXX); test -d "$d" && echo yes; rmdir "$d"'
same mktemp-fewx 'mktemp -p . ab.XX 2>/dev/null; echo $?'
same truncate-s 'truncate -s 10 words.txt; wc -c words.txt'
same truncate-grow 'truncate -s 100 nonl.txt; wc -c nonl.txt'
same truncate-plus 'truncate -s +5 nonl.txt; truncate -s -3 words.txt; wc -c nonl.txt words.txt'
same truncate-new 'truncate -s 1k newfile; wc -c newfile'
same truncate-c 'truncate -c -s 5 nosuch; echo $?; ls'
same truncate-r 'truncate -r words.txt nums.txt; wc -c nums.txt'
same realpath-basic 'realpath sub/deep/../deep/file | sed "s|^$PWD||"'
same realpath-link 'realpath link | sed "s|^$PWD||"'
same realpath-s 'realpath -s link | sed "s|^$PWD||"'
same realpath-m 'realpath -m nosuch/dir | sed "s|^$PWD||"'
same realpath-missing 'realpath nosuch/dir 2>/dev/null; echo $?'
same realpath-e 'realpath -e nosuch 2>/dev/null; echo $?'
same link-basic 'link words.txt hard; stat -c %h hard'
same unlink-basic 'unlink words.txt; ls'
same unlink-missing 'unlink nosuch 2>/dev/null; echo $?'
# whoami / groups / tty
same whoami 'whoami'
same groups 'groups'
same tty-notty 'tty < /dev/null; echo $?'
same tty-s 'tty -s < words.txt; echo $?'
# xargs / timeout
same xargs-echo 'cat words.txt | xargs'
same xargs-n 'cat words.txt | xargs -n 2'
same xargs-n1 'cat words.txt | xargs -n 1 echo got'
same xargs-I 'cat words.txt | xargs -I {} echo "<{}>"'
same xargs-0 'printf "a b\0c\0" | xargs -0 -n 1'
same xargs-quotes 'printf "\"a b\" c\n" | xargs -n 1'
same xargs-r 'printf "" | xargs -r echo nothing; echo $?'
same xargs-empty 'printf "" | xargs echo nothing'
same xargs-fail 'echo x | xargs false; echo $?'
same xargs-nocmd 'echo x | xargs nosuchcmd 2>/dev/null; echo $?'
same xargs-t 'echo a b | xargs -t echo 2>&1'
same timeout-ok 'timeout 5 echo fine; echo $?'
same timeout-expire 'timeout 0.2 sleep 5; echo $?'
same timeout-s 'timeout -s KILL 0.2 sleep 5; echo $?'
same timeout-status 'timeout 5 sh -c "exit 3"; echo $?'
same timeout-nocmd 'timeout 1 nosuchcmd 2>/dev/null; echo $?'
# expr / factor
same expr-arith 'expr 1 + 2 \* 3'
same expr-paren 'expr \( 1 + 2 \) \* 3'
same expr-div 'expr -7 / 2; expr -7 % 2; expr 7 / -2'
same expr-cmp 'expr 3 \< 5; expr abc = abc; expr abc \> abd; echo $?'
same expr-str 'expr length hello; expr substr hello 2 3; expr index hello l'
same expr-match 'expr abcdef : "ab\(c.\)"; expr abcdef : "abc"; expr abcdef : "x"; echo $?'
same expr-match-kw 'expr match foobar "fo*"'
same expr-or 'expr 0 \| 5; expr "" \| 0; echo $?; expr 2 \& 3; expr 2 \& 0; echo $?'
same expr-zero 'expr 0; echo $?'
same expr-divzero 'expr 1 / 0 2>/dev/null; echo $?'
same expr-syntax 'expr 1 + 2>/dev/null; echo $?'
same expr-plus-kw 'expr + match'
same factor-basic 'factor 1 2 12 97 360 1001'
same factor-stdin 'echo "100 65537" | factor'
same factor-big 'factor 600851475143'
same factor-bad 'factor abc 2>/dev/null; echo $?'
# sed
same sed-s 'sed "s/a/X/" words.txt'
same sed-s-g 'sed "s/a/X/g" words.txt'
same sed-s-n 'sed -n "s/alpha/ALPHA/p" words.txt'
same sed-s-amp 'sed "s/al.*/[&]/" words.txt'
same sed-s-group 'sed "s/\(.\)\(.*\)/\2\1/" words.txt'
same sed-E 'sed -E "s/(a|e)+/_/g" words.txt'
same sed-s-nth 'echo aaaa | sed "s/a/b/3"'
same sed-s-nthg 'echo aaaa | sed "s/a/b/2g"'
same sed-s-I 'sed "s/APPLE/x/I" case.txt'
same sed-s-delim 'sed "s|a|/|g" words.txt'
same sed-s-case 'sed "s/\(.*\)/\U\1/" words.txt; sed -E "s/(.)(.*)/\u\1\L\2/" case.txt'
same sed-s-newline 'sed "s/a/a\n/" words.txt'
same sed-s-empty-match 'echo abc | sed "s/x*/-/g"'
same sed-d 'sed "/a/d" words.txt'
same sed-d-range 'sed "2,4d" words.txt'
same sed-d-last 'sed "\$d" words.txt'
same sed-p 'sed -n "2p;4p" words.txt'
same sed-p-range-re 'sed -n "/beta/,/delta/p" words.txt'
same sed-p-step 'seq 10 | sed -n "1~3p"'
same sed-p-plus 'seq 10 | sed -n "/4/,+2p"'
same sed-p-mult 'seq 10 | sed -n "2,~4p"'
same sed-zero-addr 'seq 5 | sed -n "0,/1/p"; seq 5 | sed -n "1,/1/p"'
same sed-negate 'sed -n "/a/!p" words.txt'
same sed-a 'sed "2a appended" words.txt'
same sed-a-classic 'sed "2a\\
appended" words.txt'
same sed-i-cmd 'sed "1i inserted" words.txt'
same sed-c 'sed "2,3c changed" words.txt'
same sed-c-single 'sed "/gamma/c gone" words.txt'
same sed-eq 'sed -n "/a/=" words.txt'
same sed-q 'sed 3q words.txt; echo $?'
same sed-q-exit 'sed "2q5" words.txt; echo $?'
same sed-Q 'sed 3Q words.txt'
same sed-y 'sed "y/abc/ABC/" words.txt'
same sed-N 'sed "N;s/\n/+/" words.txt'
same sed-N-last 'seq 3 | sed N'
same sed-hold 'sed -n "1!G;h;\$p" words.txt'
same sed-x 'sed -n "x;\$p" words.txt'
same sed-P-D 'printf "a\nb\nc\n" | sed -n "N;P;D"'
same sed-n-cmd 'seq 6 | sed -n "n;p"'
same sed-branch 'seq 5 | sed ":a;N;\$!ba;s/\n/,/g"'
same sed-t 'echo aaa | sed ":x;s/a/b/;tx"'
same sed-T 'printf "a\nb\n" | sed "s/a/X/;Tskip;s/\$/!/;:skip"'
same sed-block 'sed -n "/a/{s/a/A/;p}" words.txt'
same sed-block-nested 'seq 10 | sed -n "/1/{/0/{p};}"'
same sed-multi-e 'sed -e "s/a/1/" -e "s/e/2/" words.txt'
same sed-script-file 'printf "s/a/1/\n2d\n" > s.sed; sed -f s.sed words.txt'
same sed-semicolon-ws 'sed "s/a/1/ ; s/e/2/" words.txt'
same sed-comment 'sed "# comment
s/a/1/" words.txt'
same sed-hash-n 'sed "#n
2p" words.txt'
same sed-nonl 'sed "s/no/NO/" nonl.txt'
same sed-multi-file 'sed -n "\$p" words.txt nums.txt'
same sed-separate 'sed -s -n "\$p" words.txt nums.txt'
same sed-inplace 'sed -i "s/a/X/g" words.txt; cat words.txt'
same sed-inplace-suffix 'sed -i.bak "1d" words.txt; cat words.txt words.txt.bak'
same sed-w 'sed -n "/a/w out.txt" words.txt; cat out.txt'
same sed-r-cmd 'sed "1r nums.txt" words.txt'
same sed-l 'printf "a\tb\001\n" | sed -n l'
same sed-z 'sed "2z" words.txt'
same sed-regex-last 'sed -n "/beta/{s//BETA/;p}" words.txt'
same sed-bad 'sed "s/a/" words.txt 2>/dev/null; echo $?'
same sed-unknown 'sed "k" words.txt 2>/dev/null; echo $?'
same sed-stdin 'cat words.txt | sed 1d'
same sed-empty-pattern-space 'printf "\n\n" | sed "s/^$/E/"'
same sed-anchors-g 'echo aaa | sed "s/^a/b/g"; echo aaa | sed "s/a\$/b/g"'
# find
same find-all 'find . | sort'
same find-name 'find . -name "*.txt" | sort'
same find-iname 'find . -iname "WORDS*" | sort'
same find-type-f 'find . -type f | sort'
same find-type-d 'find . -type d | sort'
same find-type-l 'find . -type l'
same find-maxdepth 'find . -maxdepth 1 | sort'
same find-mindepth 'find . -mindepth 2 | sort'
same find-empty 'find . -empty | sort'
same find-size 'find . -type f -size +50k | sort; find . -type f -size -1k | sort; find . -size 0 | sort'
same find-size-c 'find . -type f -size +100c -size -200000c | sort'
same find-path 'find . -path "*deep*" | sort'
same find-not 'find . -type f ! -name "*.txt" | sort; find . -type f -not -name "*.txt" | sort'
same find-or 'find . -name "nums.txt" -o -name "case.txt" | sort'
same find-paren 'find . \( -name "*.txt" -o -name "*.bin" \) -size +100c | sort'
same find-prune 'find . -name sub -prune -o -type f -print | sort'
same find-print0 'find . -name "*.txt" -print0 | tr "\0" "\n" | sort'
same find-exec 'find . -name "nu*.txt" -exec cat {} \;'
same find-exec-plus 'find . -name "*.txt" -exec echo got {} + | tr " " "\n" | sort'
same find-delete 'find . -name "*.txt" -delete; find . | sort'
same find-delete-dir 'find sub -delete; ls'
same find-newer 'touch -d @0 old; find . -newer big.bin -o -name old -prune | sort | head -1 >/dev/null; find . -newer old -type f | sort'
same find-perm 'find . -perm 640; find . -type f -perm -644 | sort; find . -perm /100 -type f'
same find-depth 'find sub -depth | sort'
same find-start 'find sub empty | sort'
same find-nomatch 'find . -name nosuch; echo $?'
same find-missing 'find nosuch 2>/dev/null; echo $?'
same find-bad 'find . -foo 2>/dev/null; echo $?'
same find-regex 'find . -regex ".*/[a-c].*txt" | sort'
same find-links 'ln words.txt w2; find . -type f -links 2 | sort'
same find-user 'find . -type f -user $(id -un) | sort'
same find-mtime 'find . -type f -mtime -1 | sort; find . -mtime +100'
same find-quit 'find . -name "*.txt" -quit; echo $?'
same find-true-false 'find . -maxdepth 0 -true; find . -false; echo $?'
# install / df
same install-file 'install words.txt dest; stat -c "%a %s" dest'
same install-m 'install -m 600 words.txt dest; stat -c %a dest'
same install-dir 'install -d -m 700 newdir/sub; stat -c "%a %F" newdir/sub'
same install-D 'install -D words.txt a/b/c; stat -c "%a" a/b/c'
same install-t 'install -t sub words.txt nums.txt; ls sub'
same install-many 'install words.txt nums.txt empty; ls empty'
same install-p 'install -p words.txt dest; test dest -nt words.txt || test words.txt -nt dest || echo same'
same df-header 'df . | head -1; echo $?'
same df-mount 'df . | wc -l; df -P / | tail -1 | wc -w'
same df-h 'df -h . | head -1'
same df-missing 'df nosuch 2>/dev/null; echo $?'
# od / hexdump
same od-default 'od words.txt'
same od-c 'od -c words.txt'
same od-x 'od -x words.txt'
same od-tx1 'od -An -tx1 words.txt'
same od-tx1-v 'od -v -tx1 big.bin | head -3'
same od-b 'od -b nonl.txt'
same od-td4 'printf "\377\377\377\377\001\000\000\000" | od -td4'
same od-tu2 'od -tu2 nums.txt'
same od-ta 'od -ta words.txt'
same od-Ax 'od -Ax -tx1 words.txt'
same od-An-c 'od -An -c nonl.txt'
same od-j 'od -j 10 -N 8 -c words.txt'
same od-dup 'head -c 64 /dev/zero | od; head -c 64 /dev/zero | od -v'
same od-stdin 'od < nums.txt'
same od-tx8 'od -tx8 words.txt'
same od-to1 'od -to1 case.txt'
same od-multi 'od -tx1 -c nonl.txt'
expect hexdump-C '00000000  61 6c 70 68 61 0a 62 65  74 61 0a 67 61 6d 6d 61  |alpha.beta.gamma|
00000010  0a 64 65 6c 74 61 0a 61  6c 70 68 61 0a           |.delta.alpha.|
0000001d
exit=0' "hexdump -C words.txt"
expect hexdump-default '0000000 3031 390a 310a 3030 2d0a 0a33 2e32 0a35
0000010
exit=0' "hexdump nums.txt"
expect hexdump-n '3
exit=0' "hexdump -C -n 20 big.bin | wc -l"
expect hexdump-s '00000010  0a 64 65 6c 74 61 0a 61  6c 70 68 61 0a           |.delta.alpha.|
0000001d
exit=0' "hexdump -C -s 16 words.txt"
expect hexdump-dup '00000000  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
*
00000040
exit=0' "head -c 64 /dev/zero | hexdump -C"
expect hexdump-b '0000000 156 157 040 164 162 141 151 154 151 156 147 040 156 145 167 154
0000010 151 156 145
0000013
exit=0' "hexdump -b nonl.txt"
expect hexdump-x '0000000    6c61    6870    0a61    6562    6174    670a    6d61    616d
0000010    640a    6c65    6174    610a    706c    6168    000a
000001d
exit=0' "hexdump -x words.txt"
# shuf / tsort / free
same shuf-sorted 'shuf words.txt | sort'
same shuf-n 'shuf -n 2 words.txt | wc -l'
same shuf-i 'shuf -i 1-5 | sort -n'
same shuf-e 'shuf -e a b c | sort'
same shuf-r 'shuf -r -n 5 -e x | uniq'
same shuf-o 'shuf -o out words.txt; sort out; rm out'
same tsort-basic 'printf "a b\nb c\na c\n" | tsort'
same tsort-order 'printf "c a\nb a\nd b\n" | tsort'
same tsort-single 'printf "x x\n" | tsort'
same tsort-loop 'printf "a b\nb a\n" | tsort 2>/dev/null; echo $?'
same tsort-odd 'printf "a b c\n" | tsort 2>/dev/null; echo $?'
same free-header 'free | head -1; free -h | wc -l; free -m | tail -1 | wc -w'
# sort keys, tr classes, tail -f, ls flags
same sort-k2 'printf "b 2\na 3\nc 1\n" | sort -k2'
same sort-k2n 'printf "b 10\na 9\nc 100\n" | sort -k2n; printf "b 10\na 9\nc 100\n" | sort -k2 -n'
same sort-t 'sort -t: -k2 fields.txt; sort -t: -k3,3r fields.txt'
same sort-k-range 'printf "x b 1\ny a 2\nz a 1\n" | sort -k2,2 -k3,3n'
same sort-k-char 'printf "abc\nabd\naba\n" | sort -k1.3'
same sort-b 'printf "  b\n a\nc\n" | sort -b; printf "  b\n a\nc\n" | sort'
same sort-s 'printf "a 2\na 1\nb 0\n" | sort -s -k1,1'
same sort-c 'sort -c words.txt 2>/dev/null; echo $?; seq 5 | sort -c; echo $?'
same sort-C 'sort -C nums.txt; echo $?'
same sort-u-key 'printf "a 1\na 2\nb 1\n" | sort -u -k1,1'
same sort-k-bad 'sort -k 0 words.txt 2>/dev/null; echo $?'
same tr-class 'echo "Hello World 123" | tr "[:upper:]" "[:lower:]"'
same tr-class-d 'echo "Hello World 123" | tr -d "[:digit:][:space:]"'
same tr-class-s 'echo "a   b    c" | tr -s "[:blank:]"'
same tr-repeat 'echo hello | tr "a-z" "[x*]"'
same tr-repeat-n 'echo hello | tr "el" "[a*2]"'
same tr-class-c 'echo "ab1!" | tr -c "[:alnum:]" _'
same touch-d 'touch -d @86400 t1; touch -d "2020-01-02 03:04:05" t2; touch -d 2001-02-03 t3; stat -c "%Y %n" t1 t2 t3'
same touch-r 'touch -r zero words.txt; test words.txt -nt zero || test zero -nt words.txt || echo same'
same touch-t 'touch -t 202001020304.05 t 2>/dev/null; echo $?'
same tail-f 'timeout 1 tail -f words.txt; echo $?'
same tail-f-grow '(sleep 0.3; echo more >> words.txt) & timeout 2 tail -f words.txt; echo $?'
same ls-r 'ls -r'
same ls-S 'ls -S'
same ls-t 'touch -d @1000 words.txt; touch -d @2000 nums.txt; ls -t | head -3; ls -tr | tail -3'
same ls-lh 'ls -lh big.bin words.txt | sed "s/[A-Z][a-z][a-z] *[0-9]* [0-9:]*//"'
same ls-i 'ls -i words.txt | wc -w; ls -i words.txt | cut -d" " -f2'
same ls-n 'ls -n words.txt | sed "s/[A-Z][a-z][a-z] *[0-9]* [0-9:]*//"'
same ls-A 'ls -A'
same ls-lS 'ls -lS | sed "s/[A-Z][a-z][a-z] *[0-9]* [0-9:]*//"'
# dd / diff
same dd-copy 'dd if=words.txt of=out status=none; cmp words.txt out; echo $?'
same dd-bs-count 'dd if=big.bin of=out bs=1000 count=3 status=none; wc -c out'
same dd-skip-seek 'dd if=big.bin of=out bs=100 skip=5 count=2 status=none; cksum out; dd if=words.txt of=out2 bs=10 seek=2 status=none; wc -c out2'
same dd-stdin 'cat words.txt | dd bs=7 status=none | cmp - words.txt; echo $?'
same dd-notrunc 'cp words.txt out; dd if=nums.txt of=out conv=notrunc status=none; cat out'
same dd-sync 'dd if=words.txt of=out bs=16 conv=sync status=none; wc -c out'
same dd-big 'dd if=big.bin of=out bs=64k status=none; cmp big.bin out; echo $?'
same dd-bad 'dd foo=bar 2>/dev/null; echo $?'
same diff-same 'diff words.txt words.txt; echo $?'
same diff-normal 'diff words.txt case.txt; echo $?'
same diff-add 'seq 5 > a; seq 7 > b; diff a b; echo $?'
same diff-del 'seq 7 > a; seq 5 > b; diff a b'
same diff-mid 'printf "a\nb\nc\nd\n" > a; printf "a\nx\ny\nd\n" > b; diff a b'
same diff-u 'printf "a\nb\nc\nd\ne\nf\ng\nh\ni\nj\n" > a; printf "a\nb\nc\nX\ne\nf\ng\nh\ni\nj\n" > b; diff -u a b | tail -n +3'
same diff-u-two 'seq 20 > a; seq 20 | sed "3d;18s/18/X/" > b; diff -u a b | tail -n +3'
same diff-u-header 'diff -u words.txt case.txt | head -2 | cut -f1'
same diff-U0 'seq 9 > a; seq 9 | sed "5d" > b; diff -U0 a b | tail -n +3'
same diff-q 'diff -q words.txt case.txt; echo $?; diff -q words.txt words.txt; echo $?'
same diff-s 'diff -s words.txt words.txt'
same diff-i 'printf "Hello\n" > a; printf "hello\n" > b; diff -i a b; echo $?; diff a b; echo $?'
same diff-w 'printf "a b\n" > a; printf "ab\n" > b; diff -w a b; echo $?; diff -b a b; echo $?'
same diff-b 'printf "a   b\n" > a; printf "a b\n" > b; diff -b a b; echo $?'
same diff-nonl 'printf "a\nb" > a; printf "a\nb\n" > b; diff a b; echo $?'
same diff-nonl-u 'printf "a\nb" > a; printf "a\nc" > b; diff -u a b | tail -n +3'
same diff-empty 'printf "" > a; diff a words.txt; echo $?'
same diff-missing 'diff nosuch words.txt 2>/dev/null; echo $?'
same diff-N 'diff -N nosuch words.txt | head -1; echo $?'
same diff-dir 'cp words.txt sub/; diff words.txt sub; echo $?'
same diff-long 'seq 1000 > a; seq 1000 | sed "500s/.*/X/;700d;900a Y" > b; diff a b'
same diff-all-diff 'seq 3 > a; seq 4 6 > b; diff a b'
# local time: date, stat, ls -l, diff -u and touch against GNU with explicit TZ
# values (zone files, POSIX TZ strings, odd names) and fixed instants
same date-tz-zones 'for z in UTC Japan EST5EDT EST5 "<+0530>-5:30" :Asia/Kolkata Asia/Kolkata "" XYZ JST-9 Europe/Dublin Australia/Lord_Howe America/St_Johns Etc/GMT+5 "NZST-12NZDT,M9.5.0,M4.1.0/3" America "<+05>-5" "EST+5EDT,M3.2.0/2,M11.1.0/2" XYZ-3:30 Factory GMT0 :UTC; do for t in 0 1700000000; do TZ=$z date -d @$t "+[$z] %F %T %z %:z %::z %:::z %Z %s"; done; done'
same date-tz-unset '(unset TZ; date -d @1700000000 "+%F %T %z %Z")'
same date-tz-dst-ny 'for t in 1710053999 1710054000 1730611799 1730611800 1730615399 1730615400 -5000000000 99999999999; do TZ=America/New_York date -d @$t "+%F %T %z %Z %s"; done'
same date-tz-dst-half 'for t in 1712413800 1712415600 1712417400 1696087800 1696089600 1696091400; do TZ=Australia/Lord_Howe date -d @$t "+%F %T %z %:::z %Z"; done'
same date-tz-lmt 'for t in -2000000000 -3000000000; do TZ=Asia/Kolkata date -d @$t "+%F %T %z %::z %:::z %Z"; done'
same date-tz-default 'TZ=America/New_York date -d @0; TZ=America/New_York date -R -d @0; TZ=Asia/Kolkata date -R -d @0; TZ=America/New_York date -u -d @0; TZ=Asia/Tokyo date -u -d @0 "+%Z %z"'
same date-tz-years 'for t in -62167219200 -62198755200 -100000000000 253402300800 -67768040609740800 99999999999999999 67767976233316800; do TZ=America/New_York date -d @$t "+%Y|%C|%y|%G|%g|%F|%s|%c|%x|%D"; echo $?; done'
same date-fmt-flags 'for c in a A b B c C d D e F g G h H I j k l m M n N p P q r R s S t T u U V w W x X y Y z Z % + Q : 1; do for p in "" E O ^ "#" - _ 0 + 6 _6 -6 06 ^6 "#6" +6 +2 3 _1 12 _12 +12 -12 ^# 0_ _0; do printf "%s=[%s] " "$p$c" "$(TZ=America/New_York date -d @1710053999 "+%$p$c")"; done; echo; done'
same date-fmt-tz 'TZ=Asia/Kolkata date -d @0 "+%::::z|%:5z|%4z|%8:z|%10::z|%_z|%-z|%0:z|%:|%::x|%E:z|%-:::z|%_10:::z|end%"; TZ=America/New_York date -d @0 "+%6%d|%%|%-%|x%5"'
same date-fmt-week 'for t in 0 86400 1104537600 1135987200 1167523200 1199145600 1230681600 1262217600 1293753600 1609372800 1609459200 1640995200 -86400 -31536000; do TZ=UTC date -d @$t "+%G-W%V-%u %g %U %W %j %a"; done'
same date-fmt-ns '/usr/bin/touch -d @1710053999.123456780 n1; /usr/bin/touch -d @1710053999.0000012 n2; for f in n1 n2; do TZ=America/New_York date -r $f "+%N|%-N|%_N|%3N|%-3N|%_3N|%12N|%-12N|%_12N|%+12N|%1N|%9N|%T.%6N %Z"; done'
same date-bad 'date -d @0 +%F extra; echo $?; date -R -d @0 +%F; echo $?'
same stat-tz '/usr/bin/touch -d @1710053999.5 f; /usr/bin/touch -a -d @1730611800 f; for z in America/New_York Asia/Kolkata UTC; do TZ=$z stat -c "%y|%x" f; TZ=$z stat f | grep -E "^(Access|Modify): [0-9]"; done'
same ls-l-tz '/usr/bin/touch -d @1000000000 old; for z in America/New_York Asia/Kolkata; do TZ=$z ls -l old | cut -d" " -f6-; done; touch new; ls -l new | cut -d" " -f6- | sed "s/[0-9][0-9]:[0-9][0-9]/HH:MM/"'
same diff-u-tz '/usr/bin/touch -d @1710053999.25 a; seq 2 > b; /usr/bin/touch -d @1730611800 b; for z in America/New_York Asia/Kolkata; do TZ=$z diff -u a b | head -2; done'
same touch-tz 'export TZ=America/New_York; touch -d "2024-07-01 12:00:00" a; touch -d "2024-11-03 01:30:00" b; touch -d 2024-01-15 c; touch -t 202411030130 d; touch -t 201612312359.60 e; stat -c "%Y %n" a b c d e; touch -d "2024-03-10 02:30:00" f; echo $?; touch -t 202403100230 f; echo $?; touch -d "2020-02-30" f; echo $?; touch -d "2016-12-31 23:59:60" f; echo $?; ls'
same touch-tz-half 'TZ=Australia/Lord_Howe touch -d "2024-04-07 01:45:00" a; TZ=Australia/Lord_Howe touch -d "2023-10-01 02:15:00" b; echo $?; stat -c "%Y %n" a'
same date-tz-tzdir 'TZDIR=/usr/share/zoneinfo/America TZ=New_York date -d @0 "+%T %Z"; TZDIR=/usr/share/zoneinfo/Asia TZ=:Kolkata date -d @0 "+%T %Z"; TZDIR= TZ=Japan date -d @0 "+%T %Z"'
# limits pinned (README "Known limits"): with an unknown zone name nelibc
# keeps UTC and its abbreviation; GNU (glibc) shows the name's leading
# letters as the abbreviation
expect date-tz-unknown-name '+0000 UTC
+0000 UTC
exit=0' 'TZ=Foo/Bar date -d @0 "+%z %Z"; TZ=:Foo date -d @0 "+%z %Z"'
# ... and a TZDIR without the zone falls back to /usr/share/zoneinfo, where
# GNU treats the name as a POSIX string (Asia, +0000)
expect date-tz-tzdir-missing '09:00:00 JST
exit=0' 'TZDIR=/nonexistent TZ=Asia/Tokyo date -d @0 "+%T %Z"'
# awk
. "$(dirname -- "$0")/awk.sh"
# sh
. "$(dirname -- "$0")/sh.sh"
# dispatch
expect list-count '87
exit=0' "$BIN --list | wc -l"

echo "nebox tests: $pass passed, $fail failed"
[ -n "$failed" ] && echo "failed:$failed"
[ "$fail" -eq 0 ]

#!/bin/sh
# nebox conformance tests. Each `same` case runs one shell command twice from
# identical fixture directories: once with the host's own utilities, once with
# nebox's applet links first on PATH. stdout, exit status, and the resulting
# directory tree must match. `expect` cases pin an exact output where the host
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
  (cd "$1" && LC_ALL=C PATH="$2$PATH" sh -c "$3" 2>"$1.err"; echo "exit=$?") > "$1.out"
}

same() { # name command
  name=$1; cmd=$2
  run_in "$W/ref" "" "$cmd"
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
same which-sh 'which sh'
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
expect ls-l-shape 'exit=0' "ls -l words.txt | grep -Eq '^-rw-r--r-- +1 +[0-9]+ +[0-9]+ +31 [A-Z][a-z]{2} +[0-9]+ [0-9:]{5} words.txt\$'"
expect grep-E-unsupported 'exit=2' "grep -E a words.txt"

echo "nebox tests: $pass passed, $fail failed"
[ -n "$failed" ] && echo "failed:$failed"
[ "$fail" -eq 0 ]

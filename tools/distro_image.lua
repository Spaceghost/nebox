-- Write the x86-64 Theseus development initramfs using the built SDK and applets.
local lfs = require 'lfs'
assert(#arg == 5 or #arg == 6, 'usage: distro_image.lua NEBOX NEBUILD NECC SDK OUTPUT.cpio [NELINKER]')

local function absolute(path)
  if path:sub(1, 1) ~= '/' then path = lfs.currentdir() .. '/' .. path end
  return (path:gsub('/+$', ''))
end

local function quote(s)
  return "'" .. s:gsub("'", "'\\''") .. "'"
end

local function capture(command)
  local pipe = assert(io.popen(command, 'r'))
  local result = assert(pipe:read('a'))
  assert(pipe:close(), 'command failed: ' .. command)
  return result
end

local nebox, nebuild, necc, sdk, output = table.unpack(arg, 1, 5)
nebox, nebuild, necc, sdk, output = absolute(nebox), absolute(nebuild), absolute(necc), absolute(sdk), absolute(output)
local nelinker = arg[6] and absolute(arg[6])
assert(nebox:match('/nebox$'), 'supply the multicall executable named nebox')
assert(not (output == sdk or output:sub(1, #sdk + 1) == sdk .. '/'), 'choose an output outside the staged SDK')
local parent = output:match('^(.*/)') or './'
local sdk_info = assert(lfs.attributes(sdk))
local ancestor = parent
while true do
  local current = assert(lfs.attributes(ancestor))
  assert(current.dev ~= sdk_info.dev or current.ino ~= sdk_info.ino, 'choose an output outside the staged SDK')
  ancestor = ancestor .. '/..'
  local above = assert(lfs.attributes(ancestor))
  if current.dev == above.dev and current.ino == above.ino then break end
end
local old = lfs.attributes(output)
for _, input in ipairs({nebox, nebuild, necc, sdk .. '/nelua-lua', sdk .. '/nlc', sdk .. '/tcc/tcc', sdk .. '/libnelibc.a', nelinker}) do
  local attr = assert(lfs.attributes(input), 'missing input: ' .. input)
  assert(not old or old.dev ~= attr.dev or old.ino ~= attr.ino, 'output aliases input: ' .. input)
end

local applets = capture(quote(nebox) .. ' --list')
local tmp = capture(quote(nebox) .. ' mktemp -d ' .. quote(parent .. '.nebox-image.XXXXXXXX')):gsub('\n$', '')
local partial = tmp .. '/rootfs.cpio'
local archive
local function build()
  archive = assert(io.open(partial, 'wb'))
  local inode = 0
  local seen = {}
  local function pad(bytes)
    assert(archive:write(string.rep('\0', (-bytes) % 4)))
  end
  local function entry(name, mode, size, major, minor)
    assert(not seen[name], 'duplicate image path: ' .. name)
    seen[name] = true
    inode = inode + 1
    local fields = {inode, mode, 0, 0, 1, 0, size, 0, 0, major or 0, minor or 0, #name + 1, 0}
    assert(archive:write('070701'))
    for _, value in ipairs(fields) do
      assert(value >= 0 and value <= 0xffffffff, 'newc field too large: ' .. name)
      assert(archive:write(('%08x'):format(value)))
    end
    assert(archive:write(name, '\0'))
    pad(110 + #name + 1)
  end
  local function small(name, mode, contents)
    entry(name, mode, #contents)
    assert(archive:write(contents))
    pad(#contents)
  end
  local function directory(name, permissions)
    entry(name, 0x4000 | (permissions or 493), 0)
  end
  local function link(name, target)
    small(name, 0xa1ff, target)
  end
  local function file(name, path, executable)
    local length = assert(lfs.attributes(path, 'size'))
    entry(name, executable and 0x81ed or 0x81a4, length)
    local input = assert(io.open(path, 'rb'))
    local copied = 0
    while true do
      local chunk, reason = input:read(65536)
      assert(not reason, reason)
      if not chunk then break end
      assert(archive:write(chunk))
      copied = copied + #chunk
    end
    assert(input:close())
    assert(copied == length, 'source changed while writing: ' .. path)
    pad(length)
  end
  local function tree(name, path)
    local names = {}
    for child in lfs.dir(path) do
      if child ~= '.' and child ~= '..' then names[#names + 1] = child end
    end
    table.sort(names)
    for _, child in ipairs(names) do
      local target, source = name .. '/' .. child, path .. '/' .. child
      local info = assert(lfs.symlinkattributes(source))
      if info.mode == 'directory' then
        directory(target)
        tree(target, source)
      elseif info.mode == 'file' then
        file(target, source, info.permissions:find('x', 1, true))
      elseif info.mode == 'link' then
        link(target, assert(lfs.symlinkattributes(source, 'target')))
      else
        error('unsupported SDK entry: ' .. source)
      end
    end
  end

  for _, name in ipairs({'bin', 'dev', 'etc', 'mnt', 'proc', 'root', 'run', 'sys', 'usr', 'usr/lib', 'usr/lib/necc'}) do
    directory(name, name == 'root' and 448 or 493)
  end
  directory('tmp', 1023) -- 01777
  entry('dev/console', 0x2180, 0, 5, 1)
  entry('dev/tty', 0x21b6, 0, 5, 0)
  entry('dev/null', 0x21b6, 0, 1, 3)
  entry('dev/zero', 0x21b6, 0, 1, 5)
  entry('dev/urandom', 0x21b6, 0, 1, 9)
  file('bin/nebox', nebox, true)
  file('bin/nebuild', nebuild, true)
  file('bin/necc', necc, true)
  if nelinker then file('bin/nelinker', nelinker, true) end
  link('init', 'bin/nebox')
  link('sbin', 'bin')
  link('usr/bin', '../bin')
  link('bin/cc', 'necc')
  link('bin/lua', '/usr/lib/necc/nelua-lua')
  link('bin/nelua-lua', '/usr/lib/necc/nelua-lua')
  for applet in applets:gmatch('%S+') do
    assert(applet ~= '.' and applet ~= '..' and not applet:find('/', 1, true), 'invalid applet: ' .. applet)
    link('bin/' .. applet, 'nebox')
  end
  assert(seen['bin/sh'], 'the supplied Nebox lacks its shell applet')
  small('etc/passwd', 0x81a4, 'root:x:0:0:root:/root:/bin/sh\n')
  small('etc/group', 0x81a4, 'root:x:0:\n')
  tree('usr/lib/necc', sdk)
  entry('TRAILER!!!', 0, 0)
  assert(archive:close())
  archive = nil
  assert(os.rename(partial, output))
end

local ok, reason = pcall(build)
if archive then pcall(archive.close, archive) end
os.remove(partial)
assert(lfs.rmdir(tmp))
assert(ok, reason)

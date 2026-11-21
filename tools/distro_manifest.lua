-- Print a nebuild manifest for Nebox and nebuild using a staged necc SDK.
local lfs = require 'lfs'
assert(#arg == 3 or #arg == 4, 'usage: distro_manifest.lua NECC SDK NEBOX_SRC [THESEUS_SRC]')

local function absolute(path)
  if path:sub(1, 1) ~= '/' then path = lfs.currentdir() .. '/' .. path end
  return (path:gsub('/%./', '/'):gsub('/+$', ''))
end

local cc, sdk, nebox = absolute(arg[1]), absolute(arg[2]), absolute(arg[3])
local theseus = arg[4] and absolute(arg[4])
local function quote(word)
  return "'" .. word:gsub("'", "'\\''") .. "'"
end

local function sources(dir, suffix, list)
  for entry in lfs.dir(dir) do
    if entry ~= '.' and entry ~= '..' then
      local path = dir .. '/' .. entry
      local kind = lfs.attributes(path, 'mode')
      if kind == 'directory' then
        sources(path, suffix, list)
      elseif kind == 'file' and path:match(suffix) then
        list[#list + 1] = path
      end
    end
  end
end

local common = {cc, sdk .. '/nelua-lua', sdk .. '/tcc/tcc', sdk .. '/tcc/libtcc1.a', sdk .. '/libnelibc.a'}
for _, dir in ipairs({'include', 'uapi', 'tcc/include'}) do
  sources(sdk .. '/' .. dir, '%.h$', common)
end
sources(sdk .. '/lib', '%.nelua$', common)
sources(sdk .. '/lualib', '%.lua$', common)

local function edge(target, src, inputs, options)
  local paths = {table.unpack(common)}
  for _, input in ipairs(inputs) do paths[#paths + 1] = input end
  table.sort(paths)
  for _, path in ipairs(paths) do
    assert(not path:find('%s'), 'nebuild manifest paths cannot contain whitespace: ' .. path)
  end
  local command = {cc, '--release', '-L', nebox .. '/src'}
  for _, option in ipairs(options) do command[#command + 1] = option end
  command[#command + 1] = src
  command[#command + 1] = '-o'
  command[#command + 1] = target
  for i, word in ipairs(command) do command[i] = quote(word) end
  io.write('build ', target, ' ', table.concat(paths, ' '), '\n')
  io.write('\tNECC_SYSROOT=', quote(sdk), ' ', table.concat(command, ' '), '\n')
end

local app_sources, options = {nebox .. '/src/nebox.nelua'}, {}
sources(nebox .. '/src/nebox', '%.nelua$', app_sources)
if theseus then
  sources(theseus .. '/src', '%.nelua$', app_sources)
  options = {'-L', theseus .. '/src', '--define', 'THESEUS_BOOT=true'}
end
edge('nebox', nebox .. '/src/nebox.nelua', app_sources, options)
local builder = nebox .. '/tools/nebuild.nelua'
edge('nebuild', builder, {builder, nebox .. '/src/nebuild/sys.nelua'}, {})
if theseus then
  local packer = nebox .. '/tools/distro_image.lua'
  local sdk_files = {}
  sources(sdk, '.', sdk_files)
  table.sort(sdk_files)
  for _, path in ipairs(sdk_files) do
    assert(not path:find('%s'), 'nebuild manifest paths cannot contain whitespace: ' .. path)
  end
  io.write('build rootfs.cpio nebox nebuild ', cc, ' ', packer, ' ', table.concat(sdk_files, ' '), '\n')
  io.write('\tNECC_SYSROOT=', quote(sdk), ' ', quote(cc), ' --lua ', quote(packer),
           ' ./nebox ./nebuild ', quote(cc), ' ', quote(sdk), ' rootfs.cpio\n')
  print('default rootfs.cpio')
else
  print('default nebox nebuild')
end

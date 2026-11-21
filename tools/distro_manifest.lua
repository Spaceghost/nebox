-- Print a nebuild manifest for the development image using a staged necc SDK.
local lfs = require 'lfs'
assert(#arg == 3 or #arg == 4 or #arg == 6 or #arg == 7 or #arg == 8,
  'usage: distro_manifest.lua NECC SDK NEBOX_SRC [THESEUS_SRC [NECC_SRC NELINKER_SRC [GRAPH [CONTROL_SRC]]]]')

local function absolute(path)
  if path:sub(1, 1) ~= '/' then path = lfs.currentdir() .. '/' .. path end
  return (path:gsub('/%./', '/'):gsub('/+$', ''))
end

local cc, sdk, nebox = absolute(arg[1]), absolute(arg[2]), absolute(arg[3])
local theseus = arg[4] and absolute(arg[4])
local necc_source = arg[5] and absolute(arg[5])
local linker_source = arg[6] and absolute(arg[6]) .. '/src'
local graph = arg[7] and absolute(arg[7])
local control_source = arg[8] and absolute(arg[8])
local function quote(word)
  return "'" .. word:gsub("'", "'\\''") .. "'"
end

local function path_token(path)
  assert(not path:find('%s'), 'nebuild manifest paths cannot contain whitespace: ' .. path)
  return path
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

local common = {sdk .. '/nelua-lua', sdk .. '/tcc/tcc', sdk .. '/tcc/libtcc1.a', sdk .. '/libnelibc.a'}
for _, dir in ipairs({'include', 'uapi', 'tcc/include'}) do
  sources(sdk .. '/' .. dir, '%.h$', common)
end
sources(sdk .. '/lib', '%.nelua$', common)
sources(sdk .. '/lualib', '%.lua$', common)

local function edge(target, src, inputs, options, compiler, linker)
  local paths = {compiler, table.unpack(common)}
  if linker then paths[#paths + 1] = linker end
  for _, input in ipairs(inputs) do paths[#paths + 1] = input end
  table.sort(paths)
  for _, path in ipairs(paths) do path_token(path) end
  local executable = compiler:sub(1, 1) == '/' and compiler or './' .. compiler
  local command = {executable, '--release'}
  for _, option in ipairs(options) do command[#command + 1] = option end
  command[#command + 1] = src
  command[#command + 1] = '-o'
  command[#command + 1] = target
  for i, word in ipairs(command) do command[i] = quote(word) end
  io.write('build ', target, ' ', table.concat(paths, ' '), '\n')
  io.write('\tNECC_SYSROOT=', quote(sdk))
  if linker then
    io.write(' NECC_NELINKER="$PWD/', linker, '"')
  elseif necc_source then
    io.write(' NECC_NELINKER=')
  end
  io.write(' ', table.concat(command, ' '), '\n')
end

local compiler, linker = cc, nil
if necc_source then
  local driver_files, linker_files = {}, {}
  sources(necc_source, '%.nelua$', driver_files)
  sources(linker_source, '%.nelua$', linker_files)
  edge('nelinker', linker_source .. '/nelinker.nelua', linker_files, {'-L', linker_source}, cc)
  edge('necc', necc_source .. '/necc.nelua', driver_files, {'-L', necc_source}, cc, 'nelinker')
  compiler, linker = 'necc', 'nelinker'
end

local app_sources, options = {}, {'-L', nebox .. '/src'}
sources(nebox .. '/src', '%.nelua$', app_sources)
if theseus then
  app_sources[#app_sources + 1] = theseus .. '/src/theseus/earlyboot.nelua'
  options = {'-L', nebox .. '/src', '-L', theseus .. '/src', '--define', 'THESEUS_BOOT=true'}
end
edge('nebox', nebox .. '/src/nebox.nelua', app_sources, options, compiler, linker)
local builder = nebox .. '/tools/nebuild.nelua'
edge('nebuild', builder, {builder, nebox .. '/src/nebox/sys.nelua'}, {'-L', nebox .. '/src'}, compiler, linker)
local native_inputs, native_args = '', ''
if graph then
  local theseus_sources = {}
  sources(theseus .. '/src', '%.nelua$', theseus_sources)
  for _, target in ipairs({
    {'theseus-init', 'init'}, {'theseusd', 'supervisor'},
    {'theseus', 'live_client'}, {'theseus-install', 'install'},
  }) do
    edge(target[1], theseus .. '/src/' .. target[2] .. '.nelua', theseus_sources, {'-L', theseus}, compiler, linker)
  end
  native_inputs = ' theseus-init theseusd theseus theseus-install ' .. path_token(graph)
  native_args = ' ' .. quote(graph)
  if control_source then
    local control_inputs = {control_source, theseus .. '/tests/command.nelua'}
    edge('control-test', control_source, control_inputs, {'-L', theseus}, compiler, linker)
    native_inputs = native_inputs .. ' control-test'
    native_args = native_args .. ' ./control-test'
  end
end
if theseus then
  local packer = nebox .. '/tools/distro_image.lua'
  local sdk_files = {}
  sources(sdk, '.', sdk_files)
  table.sort(sdk_files)
  for _, path in ipairs(sdk_files) do path_token(path) end
  local executable = necc_source and './necc' or cc
  io.write('build rootfs.cpio nebox nebuild ', compiler, linker and ' ' .. linker or '', ' ', packer,
    native_inputs, ' ', table.concat(sdk_files, ' '), '\n')
  io.write('\tNECC_SYSROOT=', quote(sdk), ' ', quote(executable), ' --lua ', quote(packer),
    ' ./nebox ./nebuild ', quote(executable), ' ', quote(sdk), ' rootfs.cpio',
    linker and ' ./nelinker' or '', native_args, '\n')
  print('default rootfs.cpio')
else
  print('default nebox nebuild')
end

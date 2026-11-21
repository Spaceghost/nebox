-- Print a nebuild manifest for the development image using a staged necc SDK.
local lfs = require 'lfs'
local native_nebox = #arg == 10 and arg[10] == '--native-nebox'
assert(#arg == 3 or #arg == 4 or #arg == 6 or #arg == 7 or #arg == 8 or #arg == 9 or native_nebox,
  'usage: distro_manifest.lua NECC SDK NEBOX_SRC [THESEUS_SRC [NECC_SRC NELINKER_SRC [GRAPH [CONTROL_SRC [STAGE_NECC [--native-nebox]]]]]]')

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
local stage_compiler = arg[9] and absolute(arg[9])
if stage_compiler then
  assert(necc_source and linker_source, 'STAGE_NECC requires NECC_SRC and NELINKER_SRC')
  -- Preserve the positional 9th argument while allowing callers to omit the
  -- optional Theseus, graph, and control sources in the staged build.
  if arg[4] == '-' then theseus = nil end
  if arg[7] == '-' then graph = nil end
  if arg[8] == '-' then control_source = nil end
end
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
  local bootstrap = stage_compiler or cc
  local bootstrap_options = {}
  if stage_compiler then bootstrap_options[#bootstrap_options + 1] = '--native' end
  local linker_options = {table.unpack(bootstrap_options)}
  linker_options[#linker_options + 1] = '-L'
  linker_options[#linker_options + 1] = linker_source
  local necc_options = {table.unpack(bootstrap_options)}
  necc_options[#necc_options + 1] = '-L'
  necc_options[#necc_options + 1] = necc_source
  edge('nelinker', linker_source .. '/nelinker.nelua', linker_files, linker_options, bootstrap)
  edge('necc', necc_source .. '/necc.nelua', driver_files, necc_options, bootstrap, 'nelinker')
  compiler, linker = 'necc', 'nelinker'
end

local app_sources, options = {}, {'-L', nebox .. '/src'}
sources(nebox .. '/src', '%.nelua$', app_sources)
if theseus then
  app_sources[#app_sources + 1] = theseus .. '/src/theseus/earlyboot.nelua'
  options = {'-L', nebox .. '/src', '-L', theseus .. '/src', '--define', 'THESEUS_BOOT=true'}
end
if native_nebox then table.insert(options, 1, '--native') end
edge('nebox', nebox .. '/src/nebox.nelua', app_sources, options, compiler, linker)
local builder = nebox .. '/tools/nebuild.nelua'
local builder_options = {'-L', nebox .. '/src'}
if stage_compiler then table.insert(builder_options, 1, '--native') end
edge('nebuild', builder, {builder, nebox .. '/src/nebox/sys.nelua'}, builder_options, compiler, linker)
local native_inputs, native_args = '', ''
if graph then
  local theseus_sources = {}
  sources(theseus .. '/src', '%.nelua$', theseus_sources)
  for _, target in ipairs({
    {'theseus-init', 'init'}, {'theseusd', 'supervisor'},
    {'theseus', 'live_client'}, {'theseus-install', 'install'},
  }) do
    local theseus_options = {'-L', theseus}
    if stage_compiler then table.insert(theseus_options, 1, '--native') end
    edge(target[1], theseus .. '/src/' .. target[2] .. '.nelua', theseus_sources,
      theseus_options, compiler, linker)
  end
  native_inputs = ' theseus-init theseusd theseus theseus-install ' .. path_token(graph)
  native_args = ' ' .. quote(graph)
  if control_source then
    local control_inputs = {control_source, theseus .. '/tests/command.nelua'}
    local control_options = {'-L', theseus}
    if stage_compiler then table.insert(control_options, 1, '--native') end
    edge('control-test', control_source, control_inputs, control_options, compiler, linker)
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

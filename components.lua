COMPONENTS = true

dofile("lua/sandbox.lua")
dofile("lua/glua/init.lua")
dofile("lua/photon/init.lua")
dofile("lua/environment.lua")

if arg[1] then
	sandbox.dofile(arg[1])
end

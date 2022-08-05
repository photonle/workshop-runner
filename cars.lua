dofile("lua/sandbox.lua")

--for k, v in pairs(sandbox.environment) do
--	print(k, v)
--end

local names = {}

EMVU = {}
EMVU.Configurations = {}
EMVU.Configurations.Supported = {}
function EMVU:OverwriteIndex(n, t) table.insert(names, n) end

Photon = {}
Photon.VehicleLibrary = {}
function Photon:OverwriteIndex() end

list = {}
function list.Set() end

hook = {}
function hook.Add() end

concommand = {}
function concommand.Add() end

net = {}
function net.Receive() end

function table.Copy(i)
	local o = {}
	for k, v in pairs(i) do
		o[k] = v
	end
	return o
end

resource = {}
function resource.AddWorkshop() end
function resource.AddFile() end
function resource.AddSingleFile() end

function AddCSLuaFile() end
function include() end
function CreateClientConVar() end
function Vector(x, y, z) return {x = x, y = y, z = z} end
function Angle(r, p, y) return {r = r, p = p, y = y} end
function Color(r, g, b, a) return {r = r, g = g, b = b, a = a or 255} end
function CurTime() return 0 end

sandbox.environment.EMVU = EMVU
sandbox.environment.Photon = Photon
sandbox.environment.list = list
sandbox.environment.hook = hook
sandbox.environment.concommand = concommand
sandbox.environment.net = net
sandbox.environment.table.Copy = table.Copy
sandbox.environment.resource = resource
sandbox.environment.AddCSLuaFile = AddCSLuaFile
sandbox.environment.include = include
sandbox.environment.CreateClientConVar = CreateClientConVar
sandbox.environment.Vector = Vector
sandbox.environment.Angle = Angle
sandbox.environment.Color = Color
sandbox.environment.CurTime = CurTime
sandbox.environment.print = function() end

if arg[1] then
	sandbox.dofile(arg[1])
	print(table.concat(names, "\n"))
end

local names = {}

EMVU = {}
function EMVU:AddAutoComponent(t, n) table.insert(names, n) end

function table.Copy(i)
	local o = {}
	if i == nil then
	    return o
    end

	for k, v in pairs(i) do
		o[k] = v
	end
	return o
end

function AddCSLuaFile() end
function include() end
function Vector(x, y, z) return {x = x, y = y, z = z} end
function Angle(r, p, y) return {r = r, p = p, y = y} end
function Color(r, g, b, a) return {r = r, g = g, b = b, a = a or 255} end

dofile(arg[1])
local out = table.concat(names, '--##--')
print(out)
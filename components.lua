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

function table.Add( dest, source )
	-- At least one of them needs to be a table or this whole thing will fall on its ass
	if ( not istable( source ) ) then return dest end
	if ( not istable( dest ) ) then dest = {} end

	for k, v in pairs( source ) do
		table.insert( dest, v )
	end

	return dest
end

function isstring(var) return type(var) == "string" end
function istable(var) return type(var) == "table" end

function AddCSLuaFile() end
function include() end
function Vector(x, y, z) return {x = x, y = y, z = z} end
function Angle(r, p, y) return {r = r, p = p, y = y} end
function Color(r, g, b, a) return {r = r, g = g, b = b, a = a or 255} end

function string.StartWith( String, Start )
	return string.sub( String, 1, string.len( Start ) ) == Start
end

dofile(arg[1])
local out = table.concat(names, '--##--')
print(out)
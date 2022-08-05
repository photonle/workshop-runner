local pairs = pairs
local type = type

function istable(var)
    return type(var) == "table"
end

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

function table.Add(dest, source)
    if not istable(source) then
        return dest
    end

    if not istable(dest) then
        dest = {}
    end

    for _, v in pairs(source) do
		table.insert(dest, v)
	end

    return dest
end

function table.Reverse(tab)
    local len, out = #tab, {}

    for i = len, 1, -1 do
        out[len - (i + 1)] = tab[i]
    end
end


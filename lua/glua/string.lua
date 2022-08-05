Format = string.format

do
    local type = type
    function isstring(var)
        return type(var) == "string"
    end
end

do
    local sub = string.sub
    function string:StartWith(prefix)
        return sub(self, 1, #prefix) == prefix
    end
end


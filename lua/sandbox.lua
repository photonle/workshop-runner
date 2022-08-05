local loadfile = loadfile
local pairs = pairs
local type = type
local setfenv = setfenv
local print = print

local default_env = {
    next = next,
    pairs = pairs,
    pcall = pcall,
    print = print,
    rawequal = rawequal,
    rawget = rawget,
    rawset = rawset,
    select = select,
    tonumber = tonumber,
    tostring = tostring,
    type = type,
    unpack = unpack,
    _VERSION = _VERSION,
    xpcall = xpcall,

    string = {
        byte = string.byte,
        char = string.char,
        find = string.find,
        format = string.format,
        gmatch = string.gmatch,
        gsub = string.gsub,
        len = string.len,
        lower = string.lower,
        match = string.match,
        rep = string.rep,
        reverse = string.reverse,
        sub = string.sub,
        upper = string.upper,
        dump = string.dump
    },
    table = {
        insert = table.insert,
        maxn = table.maxn,
        remove = table.remove,
        sort = table.sort
    },
    math = {
        abs = math.abs,
        acos = math.acos,
        asin = math.asin,
        atan = math.atan,
        atan2 = math.atan2,
        ceil = math.ceil,
        cos = math.cos,
        cosh = math.cosh,
        deg = math.deg,
        exp = math.exp,
        floor = math.floor,
        fmod = math.fmod,
        frexp = math.frexp,
        huge = math.huge,
        ldexp = math.ldexp,
        log = math.log,
        log10 = math.log10,
        max = math.max,
        min = math.min,
        modf = math.modf,
        pi = math.pi,
        pow = math.pow,
        rad = math.rad,
        random = math.random,
        randomseed = math.randomseed,
        sin = math.sin,
        sinh = math.sinh,
        sqrt = math.sqrt,
        tan = math.tan,
        tanh = math.tanh
    },
    os = {
        clock = os.clock,
        date = os.date,
        difftime = os.difftime,
        time = os.time
    }
}

module("sandbox")

environment = default_env

local function clone_env(env)
    local out = {}

    for k, v in pairs(env) do
        if type(v) == "table" then
            out[k] = clone_env(v)
        else
            out[k] = v
        end
    end

    return out
end

function dofile(filename)
    local func = loadfile(filename)
    if not func then
        return
    end

    local env = clone_env(environment)
    setfenv(func, env)

    return func()
end

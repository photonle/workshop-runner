EMVU = {}
EMVU.Configurations = {}
EMVU.Configurations.Supported = {}

if VEHICLES then
    function EMVU:OverwriteIndex(n, t) print(n) end
    EMVU.AddAutoComponent = function() end
elseif COMPONENTS then
    EMVU.OverwriteIndex = function() end
    function EMVU:AddAutoComponent(t, n) print(n) end
end


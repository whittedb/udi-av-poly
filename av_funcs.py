import json


def get_server_data(logger):
    # Read the SERVER info from the json.
    try:
        with open('server.json') as data:
            serverdata = json.load(data)
    except Exception as err:
        logger.error("av_funcs:get_server_data: failed to read server file {0}: {1}"
                     .format("server.json", err), exc_info=True)
        return False
    data.close()
    # Get the version info
    try:
        version = serverdata["credits"][0]["version"]
    except (KeyError, ValueError):
        logger.info("Version not found in server.json.")
        version = '0.0.0'
    # Split version into two floats.
    sv = version.split(".")
    v1 = 0
    v2 = 0
    if len(sv) == 1:
        v1 = int(sv[0])
    elif len(sv) > 1:
        v1 = float("%s.%s" % (sv[0], sv[1]))
        if len(sv) == 3:
            v2 = int(sv[2])
        else:
            v2 = float("%s.%s" % (sv[2], sv[3]))
    serverdata["version"] = version
    serverdata["version_major"] = v1
    serverdata["version_minor"] = v2
    return serverdata


def get_profile_info(logger):
    pvf = "profile/version.txt"
    try:
        with open(pvf) as f:
            pv = f.read().replace('\n', '')
    except Exception as err:
        logger.error("get_profile_info: failed to read  file {0}: {1}".format(pvf, err), exc_info=True)
        pv = 0
    return {"version": pv}

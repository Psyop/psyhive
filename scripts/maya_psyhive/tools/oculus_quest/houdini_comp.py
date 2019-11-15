import argparse
import subprocess
import time
import os
import glob
from pprint import pformat
from distutils.version import LooseVersion, StrictVersion


class HoudiniCombineMaps(object):
    def __init__(self, map_combination_list, reflection_mix=1.0):
        self.map_comp_hda = "{}/houdini/mapcomp.hda".format(os.path.dirname(__file__))
        self.map_combination_list = map_combination_list
        self.reflection_mix = reflection_mix

    def composite_maps(self):
        import hou
        # map_comp_hda = "//coppi/proj/cyclops_2/resources/houdini/otls/mapcomp.hda"

        n = hou.node('/img')
        ctx = n.createNode('img')
        hou.hda.installFile(self.map_comp_hda)

        print self.map_combination_list

        for [diffuse, reflection, output] in self.map_combination_list:
            tx = ctx.createNode("mapcomp")

            tx.parm("diffuse_map").set(diffuse)
            tx.parm("reflection_map").set(reflection)
            tx.parm("reflection_mix").set(self.reflection_mix)
            tx.parm("output_map").set(output)

            tx.parm("execute").pressButton()
        time.sleep(5)


def houdini_comp(map_combination_list, reflection_mix=1.0, h_ver=""):
    min_ver = "17"    # Should be 17
    hython_script = __file__.replace("\\", "/")
    # h_path = "C:/Program Files/Side Effects Software/Houdini "

    # Find all versions of Houdini
    # houdini_list = sorted(glob.glob("{}{}*".format(h_path, h_ver)))

    # if not houdini_list:
    #     # raise RuntimeError("Houdini NOT installed!! Cannot composite maps.")
    #     print "{:#^80}".format(" Houdini NOT installed!! Cannot composite maps. ")
    #     return False

    # Get the latest version
    # houdini_latest = houdini_list[-1]
    # latest_ver = os.path.basename(houdini_latest)
    # ver_num = latest_ver.split(" ")[-1]

    # houdini_version = houdini_latest.replace("\\", "/")
    # hython_exe = "{}/bin/hython.exe".format(houdini_version)

    # if LooseVersion(ver_num) >= LooseVersion(h_ver):  # houdini_version < min_ver:
    #     print "{:#^80}".format(" Houdini version below minimum '{}'!!! Check composite maps!!! ")

    map_conversion_args = []
    for map_triple in map_combination_list:
        map_conversion_args.append(",".join(map_triple))
        for _maps in map_combination_list:
            for _map in _maps:
                print ' - MAP', _map, os.path.exists(_map)
            print

    _args = [
        # "launch",
        # "hython",
        hython_script,
        "-m", str(reflection_mix),
        # "-w"
    ]
    _args.extend(map_conversion_args)

    print "ARGS: {}".format(pformat(_args))
    print 'COMMAND: launch hython -- {}'.format(' '.join(_args))

    import psylaunch
    psylaunch.launch_app('hython', args=_args)

    # subprocess.call(
    #     cmd
    # )
    return True


def main():

    print 'EXECUTING HOUDINI COMP'

    parser = argparse.ArgumentParser(description='combine textures using houdini')
    parser.add_argument('-m', '--mix', help='reflection mix', default=1.0)
    parser.add_argument('imageTriplets', help='comma separated lists of diffuse,reflection,output', nargs='+')

    try:
        args = parser.parse_args()
        reflection_mix = args.mix
        map_combination_list = args.imageTriplets
        map_combination_list = [map_combo.split(",") for map_combo in map_combination_list]
        hcm = HoudiniCombineMaps(map_combination_list, reflection_mix)
        hcm.composite_maps()
    except:
        import traceback
        traceback.print_exc()
        time.sleep(15)
        raise

    print 'HOUDINI COMP COMPLETE'

if __name__ == "__main__":
    main()

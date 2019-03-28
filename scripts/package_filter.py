#! /usr/bin/python2

import sys
import os
import urllib
import yaml
import subprocess

def main(output_path='.',
         ros_distro_name='kinetic'
         ):
    alpine_packages = []

    ros_dirsto_url = 'https://' + "/".join([
        'raw.githubusercontent.com',
        'ros',
        'rosdistro',
        'master',
        ros_distro_name,
        'distribution.yaml'
    ])

    tag_line = "ros-{}-".format(ros_distro_name)
    tag_line_len = len(tag_line)

    end_part = "-dbg"
    end_part_len = len(end_part)

    # Get the available packages in the target alpine distribution
    alpine_packages = subprocess.check_output(['apk', 'search', '-q']).splitlines()
    alpine_packages = [x[tag_line_len:] for x in alpine_packages if x[:tag_line_len] == tag_line]

    # Remove -dbg packages
    alpine_packages = filter(lambda x: x[-end_part_len:] != end_part, alpine_packages)

    # Remove duplicates from alpine_packages
    alpine_packages = list(set(alpine_packages))

    # Get the ros distribution file
    ros_distro = yaml.load(urllib.urlopen(ros_dirsto_url).read())

    # Extract just the keys
    ros_packages = ros_distro['repositories'].keys()

    # Match the two
    common_packages = []
    for ros_package in ros_packages:
      if ros_package in alpine_packages:
        common_packages.append(ros_package)
      elif 'release' in ros_distro['repositories'][ros_package]:
        if 'packages' in ros_distro['repositories'][ros_package]['release'].keys():
          for ros_sub_package in ros_distro['repositories'][ros_package]['release']['packages']:
            if ros_sub_package in alpine_packages:
              common_packages.append(ros_package)
              break

    # Remove any duplicates
    common_packages = list(set(common_packages))


    # Find the ros packages not available in alpine
    exclude_packages = list(set(ros_packages).difference(set(common_packages)))

    num_packages_original = len(ros_distro['repositories'].keys())

    # Remove excluded packages from the ros_distro dictionary
    for exclude_package in exclude_packages:
      del ros_distro['repositories'][exclude_package]

    # print("Distribution file was filtered from {} packages down to {}".format(num_packages_original,
    #                                                                           len(ros_distro['repositories'].keys())))

    # Swap the release platform from 'ubuntu' to 'alpine'
    ros_distro['release_platforms']['alpine'] = ['3.7']
    del ros_distro['release_platforms']['ubuntu']

    # Export the updated distribution.yaml
    output_file = "{}/distribution.yaml".format(output_path)
    with open(output_file, 'w') as f:
      f.write("%YAML 1.1\n")
      f.write("# ROS distribution file\n")
      f.write("# see REP 143: http://ros.org/reps/rep-0143.html\n")
      f.write("---\n")
      yaml.dump(ros_distro, f, default_flow_style=False)

    # os.system("chmod 777 {}".format(output_file))
    # print("Updated distribution file")
    os.system("cat {}".format(output_file))

if __name__=="__main__":
    if len(sys.argv) != 3:
        print("Wrong number of arguments")
        print("run with: package_filter.py output_path ros_distro_name")
    else:
        main(output_path=sys.argv[1],
             ros_distro_name=sys.argv[2])

#! /usr/bin/python2

import sys
import os
import urllib
import yaml
import subprocess

def get_alpine_packages():
    command = [
        'apk',
        'search',
        '-q'
    ]
    dbg_postfix = "-dbg"
    dbg_postfix_len = len(dbg_postfix)

    doc_postfix = "-doc"
    doc_postfix_len = len(dbg_postfix)

    # Capture output - apk update must have been run first
    out = subprocess.check_output(command).splitlines()
    # Filter out debug and documentation packages
    out = filter(lambda x: x[-dbg_postfix_len:] != dbg_postfix, out)
    out = filter(lambda x: x[-doc_postfix_len:] != doc_postfix, out)
    # Remove duplicates
    out = list(set(out))

    return out


def filter_distribution(alpine_packages,
                        ros_distro_name='kinetic'):

    ros_dirsto_url = 'https://' + "/".join([
        'raw.githubusercontent.com',
        'ros',
        'rosdistro',
        'master',
        ros_distro_name,
        'distribution.yaml'
    ])

    ros_tagline = "ros-{}-".format(ros_distro_name)
    ros_tagline_len = len(ros_tagline)

    # Filter out the ros-[distro] packages
    alpine_ros_packages = [x for x in alpine_packages if x[:ros_tagline_len] == ros_tagline]

    # Remove the ros-[distro] prefix
    alpine_ros_packages = [x[ros_tagline_len:] for x in alpine_ros_packages]

    # Swap hyphens for undescores
    alpine_ros_packages = list(map(lambda x: x.replace('-', '_'), alpine_ros_packages))

    # Previous steps kept separate for clairty

    # Get the ros distribution file
    ros_distro = yaml.load(urllib.urlopen(ros_dirsto_url).read())

    # Extract just the keys
    ros_packages = ros_distro['repositories'].keys()

    # Match the two
    common_packages = []
    for ros_package in ros_packages:
        if ros_package in alpine_ros_packages:
            common_packages.append(ros_package)
        elif 'release' in ros_distro['repositories'][ros_package]:
            if 'packages' in ros_distro['repositories'][ros_package]['release'].keys():
                for ros_sub_package in ros_distro['repositories'][ros_package]['release']['packages']:
                    if ros_sub_package in alpine_ros_packages:
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

    print("{}/distribution.yaml file was filtered from {} packages down to {}".format(ros_distro_name,
                                                                                      num_packages_original,
                                                                                      len(ros_distro['repositories'].keys())))

    # Swap the release platform from 'ubuntu' to 'alpine'
    ros_distro['release_platforms']['alpine'] = ['3.7']
    del ros_distro['release_platforms']['ubuntu']

    # Export the updated distribution.yaml
    output_file = "/rosdistro/{}/distribution.yaml".format(ros_distro_name)
    with open(output_file, 'w') as f:
        f.write("%YAML 1.1\n")
        f.write("# ROS distribution file\n")
        f.write("# see REP 143: http://ros.org/reps/rep-0143.html\n")
        f.write("---\n")
        yaml.dump(ros_distro, f, default_flow_style=False)

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.load(f.read())


def update_yaml(original_packages, update_packages):
    for package_name in update_packages:
        if package_name in original_packages.keys():
            if 'alpine' in original_packages[package_name]:
                if len(update_packages[package_name]['alpine']) == 0:
                    # Remove the entry
                    print("To '{}': removing all entries".format(package_name))
                    del original_packages[package_name]['alpine']
                else:
                    print("To '{}':, updating {} to {}.".format(package_name,
                                                                original_packages[package_name]['alpine'],
                                                                update_packages[package_name]['alpine']))
                    original_packages[package_name]['alpine'] = update_packages[package_name]['alpine']
            else:
                print("To '{}': adding {}".format(package_name,
                                                  update_packages[package_name]['alpine']))

                original_packages[package_name]['alpine'] = update_packages[package_name]['alpine']


def filter_rosdep(alpine_packages,
                  ros_distro_name='kinetic'):

    rosdep_url = 'https://' + "/".join([
        'raw.githubusercontent.com',
        'ros',
        'rosdistro',
        'master',
        'rosdep'
    ])
    rosdep_system_url = rosdep_url + '/base.yaml'
    rosdep_python_url = rosdep_url + '/python.yaml'

    ros_tagline = "ros-{}-".format(ros_distro_name)
    ros_tagline_len = len(ros_tagline)

    # Filter the system packages
    alpine_packages = [x for x in alpine_packages if x[:ros_tagline_len] != ros_tagline]

    alpine_python_packages = [x for x in alpine_packages if x[:3] == 'py-']
    alpine_system_packages = list(set(alpine_packages) - set(alpine_python_packages))

    # Fetch rosdep yaml files
    rosdep_python_yaml = yaml.load(urllib.urlopen(rosdep_python_url).read())
    rosdep_system_yaml = yaml.load(urllib.urlopen(rosdep_system_url).read())

    # Fetch hand coded lookups
    rosdep_python_manual_packages = load_yaml("/manual_entries_python.yaml")
    rosdep_system_manual_packages = load_yaml("/manual_entries_base.yaml")

    addition_count = 0
    for rosdep_python_pkg in [x for x in rosdep_python_yaml if 'alpine' not in rosdep_python_yaml[x]]:
        pkg_alpine_format = rosdep_python_pkg.replace('python', 'py')
        if pkg_alpine_format in alpine_python_packages:
            addition_count += 1
            rosdep_python_yaml[rosdep_python_pkg]['alpine'] = [pkg_alpine_format]

    output_file = "/rosdistro/rosdep/python.yaml"
    with open(output_file, 'w') as f:
        yaml.dump(rosdep_python_yaml, f)

    print("Added {} packages to rosdep/python.yaml".format(addition_count))

    addition_count = 0
    for rosdep_system_pkg in [x for x in rosdep_system_yaml if 'alpine' not in rosdep_system_yaml[x]]:
        if rosdep_system_pkg in alpine_system_packages:
            addition_count += 1
            rosdep_system_yaml[rosdep_system_pkg]['alpine'] = [rosdep_system_pkg]
        else:
            rosdep_dev_pkg_name = rosdep_system_pkg + "-dev"
            if rosdep_system_pkg[-4:] != "-dev":
                if rosdep_dev_pkg_name not in rosdep_system_yaml.keys():
                    if rosdep_dev_pkg_name in alpine_system_packages:
                        addition_count += 1
                        if 'alpine' in rosdep_system_yaml[rosdep_system_pkg]:
                            rosdep_system_yaml[rosdep_system_pkg]['alpine'] += [rosdep_dev_pkg_name]
                        else:
                            rosdep_system_yaml[rosdep_system_pkg]['alpine'] = [rosdep_dev_pkg_name]

    # Process any manual entries
    if rosdep_system_manual_packages is not None and len(rosdep_system_manual_packages) > 0:
        print("Making manual modifications to rosdep/base.yaml")
        update_yaml(rosdep_system_yaml, rosdep_system_manual_packages)

    if rosdep_python_manual_packages is not None and len(rosdep_python_manual_packages) > 0:
        print("Making manual modifications to rosdep/python.yaml")
        update_yaml(rosdep_python_yaml, rosdep_python_manual_packages)


    output_file = "/rosdistro/rosdep/base.yaml"
    with open(output_file, 'w') as f:
        yaml.dump(rosdep_system_yaml, f)
    print("Added {} packages to rosdep/base.yaml".format(addition_count))


if __name__=="__main__":
    if len(sys.argv) != 2:
        print("Wrong number of arguments")
        print("run with: package_filter.py ros_distro_name")
    else:
        alpine_packages = get_alpine_packages()
        if len(alpine_packages) == 0:
            print("No alpine packages were found.")
            pritn("Please run apk update first.")
        # filter_distribution(alpine_packages, ros_distro_name=sys.argv[1])
        filter_rosdep(alpine_packages, ros_distro_name=sys.argv[1])


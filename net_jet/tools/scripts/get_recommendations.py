import yaml
import os
from pprint import pprint

base_dir = os.path.dirname(os.path.abspath(__file__))


def recommendations():
    with open((os.path.join(base_dir, "recommendations_v01.yml")), encoding="utf-8") as f:
        recommends = yaml.safe_load(f)
    return recommends


recommends_repo = recommendations()


"""
OPEN RECOMMENDATIONS YAML FILE AND A DICTIONARY OF SHOW INTERFACE COMMAND
THEN CHECK THE NUMBER OF ERRORS ON THE INTERFACE AND RETURN THE RECOMMENDATIONS
"""


def get_intf_recommends(error_dict, recommends=recommends_repo):
    print(error_dict)
    result = {}
    # compare info from the network devices
    try:
        input_errors = int(error_dict['input_errors'])
        output_errors = int(error_dict['output_errors'])

        if input_errors < 10 and output_errors < 10:
            result['errors_intf_rcm'] = recommends['intf_err_less_10']
        elif input_errors > 10 and output_errors > 10:
            result['errors_intf_rcm'] = recommends['intf_err_more_10']

        if error_dict['icmp_percent']:
            icmp_percent = int(error_dict['icmp_percent'])
            delay = error_dict['delay']
            print(error_dict['delay'])
            if icmp_percent < 80:
                result['ping_rcm'] = recommends['ping_lost_more_2']
                min_d, middle_d, max_d = delay.split('/')
                if int(middle_d) > 100:
                    result['delay_rcm'] = recommends['ping_delay_more_100']
            elif icmp_percent > 80:
                result['ping_rcm'] = recommends['ping_stable']
                result['delay_rcm'] = recommends['ping_delay_less_100']

        if error_dict['icmp_pcent']:
            icmp_percent = int(error_dict['icmp_pcent'])
            delay = error_dict['delay']
            print(error_dict['delay'])
            if icmp_percent < 80:
                result['ping_rcm'] = recommends['ping_lost_more_2']
                min_d, middle_d, max_d = delay.split('/')
                if int(middle_d) > 100:
                    result['delay_rcm'] = recommends['ping_delay_more_100']
            elif icmp_percent > 80:
                result['ping_rcm'] = recommends['ping_stable']
                result['delay_rcm'] = recommends['ping_delay_less_100']
    except Exception as e:
        print(e)
    return result

from pandas import Series, DataFrame

from Gen_Utils import *

from analyzer import *
from typing import Union, List, Dict, Tuple, Any
import logging
from paretoset import paretoset
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from adjustText import adjust_text


def analyze(deployment_info_json: Union[dict, str], plot:bool = True) -> tuple[list[dict], Any, Any]:
    create_credentials()
    deployment_dict = {}

    if type(deployment_info_json) == str:
        if not exists(deployment_info_json):
            logging.error('FILE NOT FOUND ERROR:: %s' % deployment_info_json)
            raise 'FILE NOT FOUND ERROR'
        else:
            with open(deployment_info_json, 'r') as f:
                deployment_dict = json.load(f)
    else:
        deployment_dict = deployment_info_json

    analyzer_list: List[AnalyzerInterface] = []
    aws = AWSAnalyzer()
    gcp = GCPAnalyzer()

    analyzer_list.append(aws)
    analyzer_list.append(gcp)
    result_list = []
    for analyzer in analyzer_list:
        # t, c, n, results_all = cost_model.analyze(deployment_dict=deployment_dict, assumed_invocations=1000000)
        results_all = analyzer.analyze(deployment_dict=deployment_dict, assumed_invocations=1000000)
        if results_all is not None:
            result_list.append(results_all)

    avg_et = []
    avg_rtt = []
    c2 = []
    names = []

    for prov in result_list:
        for e in prov:
            avg_et.append(e.get('avg_ET'))
            avg_rtt.append(e.get('avg_RTT'))
            c2.append(e.get('cost'))
            names.append(e.get('provider') + '_' + e.get('region') + '_' + str(e.get('MB')))

    clouds_avg_et = pd.DataFrame({'avg_ET': avg_et, 'cost': c2})
    clouds_avg_rtt = pd.DataFrame({'avg_RTT': avg_rtt, 'cost': c2})
    mask = paretoset(clouds_avg_et, sense=["min", "min"])
    mask2 = paretoset(clouds_avg_rtt, sense=["min", "min"])
    paretoset_et = clouds_avg_et[mask]
    paretoset_rtt = clouds_avg_rtt[mask2]

    print('rtt', paretoset_rtt)

    # plot avg ET
    function_name = deployment_dict['function_name']
    plt.title(function_name + ' Agv ET')
    plt.scatter(avg_et, c2, zorder=10, marker='x', label="All Functions", s=50, alpha=0.8)

    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)

    plt.scatter(
        paretoset_et["avg_ET"],
        paretoset_et["cost"],
        zorder=5,
        label="Pareto Front",
        s=150,
        alpha=0.2
        )

    # texts = []
    # for i, txt in enumerate(names):
    #     if avg_et[i] in paretoset_et['avg_ET'].to_dict().values():
    #         texts.append(plt.text(avg_et[i], c2[i], txt))
    plt.legend()
    time_step = (max(avg_et) - min(avg_et)) / 10
    time_min = min(avg_et) - time_step
    time_max = max(avg_et) + time_step
    cost_step = (max(c2) - min(c2)) / 10
    cost_min = min(c2) - cost_step
    cost_max = max(c2) + cost_step
    plt.xlim([time_min, time_max])
    plt.ylim([cost_min, cost_max])
    plt.xlabel("avg_ET")
    plt.ylabel("cost")
    plt.grid(True, alpha=0.2, ls="--", zorder=0)
    plt.tight_layout()
    filename = deployment_dict['function_name']
    # adjust_text(texts, arrowprops=dict(arrowstyle="->", color='r', lw=0.5))
    plt.savefig(filename + '_avgET.png', dpi=100)
    plt.show()

    # RTT
    function_name = deployment_dict['function_name']
    plt.title(function_name + ' avg RTT')
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)

    plt.scatter(avg_rtt, c2, zorder=10, marker='x', label="All Functions", s=50, alpha=0.8)

    plt.scatter(
        paretoset_rtt["avg_RTT"],
        paretoset_rtt["cost"],
        zorder=5,
        label="Pareto Front",
        s=150,
        alpha=0.2
        )

    # texts = []
    # for i, txt in enumerate(names):
    #     if avg_rtt[i] in paretoset_rtt['avg_RTT'].to_dict().values():
    #         texts.append(plt.text(avg_rtt[i], c2[i], txt))
    plt.legend()
    time_step = (max(avg_rtt) - min(avg_rtt)) / 10
    time_min = min(avg_rtt) - time_step
    time_max = max(avg_rtt) + time_step
    cost_min = min(c2) - cost_step
    cost_max = max(c2) + cost_step
    plt.xlim([time_min, time_max])
    plt.ylim([cost_min, cost_max])
    plt.xlabel("avg_RTT")
    plt.ylabel("cost")
    plt.grid(True, alpha=0.2, ls="--", zorder=0)
    plt.tight_layout()
    filename = deployment_dict['function_name']
    plt.savefig(filename + '_avgRTT.png', dpi=100)
    # adjust_text(texts, arrowprops=dict(arrowstyle="->", color='r', lw=0.5))
    plt.savefig(filename + '_avgRTT.png', dpi=100)
    plt.show()

    return result_list, paretoset_et, paretoset_rtt
    # export_json_to_file(deployment_dict['function_name'] + '_results.json', deployment_dict)


# calculate_costs('deployment_scenario_3_result.json')


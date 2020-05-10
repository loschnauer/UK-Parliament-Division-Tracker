import numpy as np
import pandas as pd
import requests
from io import StringIO
import networkx as nx
from networkx.algorithms.centrality import closeness_centrality
import os
import re

def aggregate_voting_data(dataset):
    source_root = 'https://www.publicwhip.org.uk/data/'

    division_file = 'votematrix-{}.dat'.format(dataset)
    mpid_file = 'votematrix-{}.txt'.format(dataset)

    url = source_root + division_file
    req = requests.get(url)
    df_divisions = pd.read_table(StringIO(req.text), sep=r'\t')

    url = source_root + mpid_file
    req = requests.get(url)

    # get row where MP mapping starts
    temp = req.text.split('firstname')[0]
    skiprows = temp.count('\n') - 1
    df_mps = pd.read_table(StringIO(req.text), sep=r'\t', skiprows=skiprows)
    df_mps = df_mps[['mpid', 'firstname', 'surname', 'party']]
    df_mps['displayname'] = df_mps.apply(
        lambda x: '{},{}. ({})'.format(x['surname'], x['firstname'][0], x['party']), axis=1)

    # some cleaning and checking
    df_divisions['date'] = pd.to_datetime(df_divisions['date'])
    df_mps.set_index('mpid', inplace=True)

    return df_divisions, df_mps


def build_voting_graphs(votes, mp_mapping, edge_threshold):
    """
    Params
    -------
    votes: pd.DataFrame,
           contains votes registered by MPs for each division (row)
    mp_mapping: pd.DataFrame,
           contains mapping of unique mpid to name and party of MP
    edge_threshold: float,
           no edge will be drawn between two MP nodes in graph if percentage of votes
           they have in common is less than threshold

    Returns
    -------
    graphs: list,
            contains Networkx graph objects for each division year
    """

    vote_map = dict(aye=2, nay=4)

    # color codes
    _clr_blue = {'r': "0", 'b': "220", 'g': "0", 'a': "0.7"}
    _clr_light_blue = {'r': "30", 'b': "240", 'g': "240", 'a': "0.7"}
    _clr_red = {'r': "220", 'b': "0", 'g': "0", 'a': "0.7"}
    _clr_yellow = {'r': "250", 'b': "50", 'g': "250", 'a': "0.7"}
    _clr_orange = {'r': "250", 'b': "0", 'g': "130", 'a': "0.7"}
    _clr_green = {'r': "0", 'b': "0", 'g': "220", 'a': "0.7"}
    _clr_black = {'r': "70", 'b': "70", 'g': "70", 'a': "0.7"}

    party_clr_map = dict(Con=_clr_blue, Lab=_clr_red, LDem=_clr_yellow, SNP=_clr_orange, Green=_clr_green,
                         DUP=_clr_light_blue)

    graphs = []

    division_years = votes['date'].dt.year.unique()
    for year in sorted(division_years):

        df = votes[votes['date'].dt.year == year]
        df = df[[col for col in df.columns if 'mpid' in col]]
        # exclude individuals who were not MPs during the period or who have only missing records
        df = df.dropna(axis=1, how='all')
        bool_votes = df.isin(vote_map.values()).any(axis=0)
        drop_mps = list(bool_votes[~bool_votes].index)
        df = df.drop(drop_mps, axis=1)

        #get total number of registered votes for each mpid
        total_votes = df[df.isin(vote_map.values())].count(axis=0)

        all_mps = df.columns
        from itertools import combinations
        all_mp_pairs = combinations(all_mps, 2)
        common_votes = {}
        for pair in all_mp_pairs:
            common_votes[pair] = 0

        for vote in df.index:
            ayes = df.loc[vote].where(df.loc[vote] == vote_map['aye']).dropna().index
            nays = df.loc[vote].where(df.loc[vote] == vote_map['nay']).dropna().index

            aye_pairs = combinations(ayes, 2)
            nay_pairs = combinations(nays, 2)

            for pair in aye_pairs:
                if isinstance(common_votes.get(pair), int):
                    common_votes[pair] += 1
                # MP pair is stored in reverse order
                else:
                    common_votes[(pair[1], pair[0])] += 1

            for pair in nay_pairs:
                if isinstance(common_votes.get(pair), int):
                    common_votes[pair] += 1
                # MP pair is stored in reverse order
                else:
                    common_votes[(pair[1], pair[0])] += 1


        #some MPs have duplicate entries with different mpids,
        #nodes are added to graph by names instead of mpids to avoid counting twice
        graph = nx.Graph()
        all_mp_displaynames = list(set(mp_mapping.loc[[int(i.strip('mpid')) for i in all_mps]]['displayname']))
        for mp_display in all_mp_displaynames:
            #nodes are colored by party
            mp_party = re.search('\(([^)]+)', mp_display).group(1)
            graph.add_node(mp_display, party=mp_party, viz={'color': party_clr_map.get(mp_party, _clr_black)})

        for pair, votes_count in common_votes.items():
            mp_display1 = mp_mapping.loc[int(pair[0].strip('mpid')), 'displayname']
            mp_display2 = mp_mapping.loc[int(pair[1].strip('mpid')), 'displayname']

            # Don't draw an edge for MPs with less than threshold % votes in common during period
            #Some MPs have less registered votes: we take the minimum of the total observed votes for the two MPs
            # to compare the votes in common against
            mp1_total_votes, mp2_total_votes = total_votes.loc[pair[0]], total_votes.loc[pair[1]]

            voting_similarity = float(votes_count / min(mp1_total_votes, mp2_total_votes))
            if voting_similarity > edge_threshold:
                graph.add_edge(mp_display1, mp_display2, weight=voting_similarity, difference=1 - voting_similarity)

        print("year: {}".format(year))
        print("MPs: {}".format(len(graph.nodes())))
        print("Edges: {}".format(len(graph.edges())))

        gexf_filename = 'uk_voting_{}_{}sim.gexf'.format(year, edge_threshold)
        nx.write_gexf(graph, os.path.join('graph files NEW 0x5', gexf_filename))
        graphs.append(graph)

    return graphs



def main():
    publicwhip_datasets = [1997, 2001, 2005, 2010, 2015, 2017]

    for dataset in publicwhip_datasets:
        division_counts, mp_mapping = aggregate_voting_data(dataset)

        threshold = 0.5
        graphs = build_voting_graphs(division_counts, mp_mapping, edge_threshold=threshold)


if __name__ == '__main__':
    main()

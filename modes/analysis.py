import numpy as np
import pandas as pd
import igraph as ig
import louvain as lv

from config.CONFIG import CONFIG
from .functions import create_set

data_loc = r"data/aggregate/week1.csv"


def read_raw_data(data_loc=data_loc):
    """Collect data from a csv file to locate decklists in and return DataFrame
    of decklists.
    Parameters:
    -----------
    data_loc: string or filepath - location of the csv file to open.
    Returns:
    --------
    pandas DataFrame containing three columns ["Deck 1 List", "Deck 2 List",
    "Deck 3 List"], each of which contains a set detailing each card in that
    decklist as detected by create_set.
    See also:
    ---------
    create_set
    """
    df = pd.read_csv(data_loc)
    df = df.dropna().reset_index().loc[:, ["Deck 1 List", "Deck 2 List", "Deck 3 List"]]
    df = df.applymap(create_set)

    # print(df)
    return df


def main():
    """Handle taking input and then producing output.
    """
    df = read_raw_data()
    all_cards = set()
    # print(all_cards)
    # raise Exception
    for index, row in df.iterrows():
        for deck in row:
            all_cards = all_cards | deck

    card_data_df = pd.DataFrame(list(all_cards), columns=["Card"]).sort_values(
        by="Card"
    )
    card_data_df.set_index("Card", inplace=True)
    card_data_df["Count"] = 0
    card_data_df["Decks"] = [set() for _ in range(len(card_data_df))]

    decks = df.values.flatten().tolist()

    for i in range(len(decks)):
        for card in decks[i]:
            card_data_df.at[card, "Decks"].add(i)

    card_data_df["Count"] = card_data_df["Decks"].apply(len)
    card_data_df.sort_values(
        by=["Count", "Card"], inplace=True, ascending=[False, True]
    )
    card_data_df.reset_index(inplace=True)
    G = ig.Graph()
    G.add_vertices(len(card_data_df.index))
    for card1 in range(len(card_data_df.index) - 1):
        for card2 in range(card1 + 1, len(card_data_df.index)):
            union = card_data_df.at[card1, "Decks"] & card_data_df.at[card2, "Decks"]
            if union:
                G.add_edge(card1, card2, weight=len(union))
    G.vs["label"] = card_data_df["Card"].tolist()
    G.vs["name"] = G.vs["label"]

    partition = lv.find_partition(
        G, lv.CPMVertexPartition, weights="weight", resolution_parameter=1
    )

    clusters = 0
    
    card_data_df["Cluster"] = [set() for _ in card_data_df.index]
    
    for cluster in partition:
        for card in cluster:
            card_data_df.at[card, "Cluster"].add(clusters)
        clusters += 1
        
    G.vs["cluster"] = card_data_df["Cluster"].tolist()

    
    changed = True
    
    while changed:
        changed = False
        
        copy_df = card_data_df.copy()
        
        adjlist = G.get_adjlist()
        for card in copy_df.index:
            adjlist_card = adjlist[card]
            clus1 = copy_df.at[card, "Cluster"]
            adjclus = np.zeros(clusters)
            
            for adjcard in adjlist_card:
                clus2 = copy_df.at[adjcard, "Cluster"]
                for cluster in clus2:
                    adjclus[cluster] += 1
            
            clusfilter = [c in clus1 for c in range(clusters)]
            
            if np.sum(adjclus[clusfilter]) / np.sum(adjclus) < CONFIG["cluster_percentage"]:
                adjclus[clusfilter] = 0
                card_data_df.at[card, "Cluster"].add(np.argmax(adjclus))
                changed = True
                

    for edge in G.es:
        src_clus = card_data_df.at[edge.source, "Cluster"]
        tar_clus = card_data_df.at[edge.target, "Cluster"]
        if src_clus & tar_clus:
            edge["interior"] = 1
        else:
            edge["interior"] = 0
    # print(card_data_df)
    ig.plot(partition)
    G.save(r"C:\tmp\cards.graphml")

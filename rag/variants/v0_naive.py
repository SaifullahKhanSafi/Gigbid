def rank(index, query, requirements):
    return index.order(index.dense(query))

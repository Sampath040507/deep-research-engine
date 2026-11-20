from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain
from rich import print

def run_research_pipeline(topic: str)-> dict:
    state = {} #the dictionary we r going to return

    #WORKING OF SEARCH AGENT:
    print("\n"+" ="*50)
    print("step1 - search agent is working....")
    print("="*50)

    search_agent = build_search_agent()
    search_result = search_agent.invoke(
        {"messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]}
    )
    #create_agent expects input in the form of dict with key "messages" where messages is a list contaning a dictionary with KEYS :- "role" and "content"(but here u just simply pass the VALUES in a tuple). here role is "user" adn content ....note that content here have a placeholder. you don't have to worry about the how the placeholder is getting filled -> it is done simply when calling the run_research_pipeline itself since u can observe its parameter which is topic.

    #The content here which is the input message first goes to the LLM. The LLM then decides WHETHER to call the web_search tool and what query to pass to it. Does the LLM pass the same query to the tool? Not necessarily!

    #now we neeed the output given by agent but only the final text output or final text content, we shall store it.
    #since this project is based on multiple agent calls and multiple chain calles so we need to maintain a state: whose name is "state" here
    state['search_results'] = search_result["messages"][-1].content
    #it was empty dictionary previously and now we added a key with its value as the final text content of search_agent.

    print("\n search result: \n", state['search_results'])


    #WORKING OF READER AGENT:
    print("\n"+" ="*50)
    print("step 2 - Reader agent is scraping top resources ...")
    print("="*50)

    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages": [("user",
                f"Based on the following search results about '{topic}', "
                f"pick the most relevant URL and scrape it for deeper content.\n\n"
                f"Search Results:\n{state['search_results'][:1000]}"  # you might find those links in the first 1000 characters. - written only due to api pricing.
                )]
    })
    #what does reader_agent expect as input? if u back trace then through the build_reader_agent, it uses llm to scrape the "urls" but how those urls are scraped - llm decides to use web_scrape tool. "urls" or the links are the input- how r we going to get all them- we r gonna get'em from above search results(we saved them in the memory that we r maintaining - "state")

    state['scraped_content'] = reader_result["messages"][-1].content
    print("\n scraped content: \n", state['scraped_content'])

    #EXECUTING THE WRITER CHAIN: 
    print("\n"+" ="*50)
    print("step 3 - Writer is drafting the report ...")
    print("="*50)

    #we have to invoke the chain to execute but we have to pass something as input to invoke which is? input for writer_prompt is the required input and what writer_prompt is expecting {topic} and {research}. for this research we are going to send both the above results : search results and scraped content - so inorder to pass them in one variable we shall combine the outputs for that:

    research_combined = (
        f"SEARCH RESULTS: \n {state['search_results']}\n\n"
        f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
    )

    state['report']= writer_chain.invoke({
        "topic": topic, 
        "research": research_combined
    })
    #key names here should match the names of the to-be-embed-expressions of writer_prompt obv ukw! and the topic is RHS is the topic passed when calling this run_research_pipeline func.
    #we shall add the writer chain's result to our memeory "state"; saving it also helps in generating the feedback which is the critic since critic_prompt needs {report}. saved content here can be passed to {report}

    print("\n Final Report: \n",state['report'])

    #EXECUTING THE CRIITC CHAIN: 
    print("\n"+" ="*50)
    print("step 4 - critic is reviewing the report ")
    print("="*50)

    state['feedback'] = critic_chain.invoke({
        "report": state['report']
    })

    print("\n critic report \n", state['feedback'])

    #now when u call the function it keeps on printing all the stuff we wrote above but it isn't returning anything:
    return state

if __name__ == "__main__":
    topic = input("enter a topic which you want to research on:")
    run_research_pipeline(topic)
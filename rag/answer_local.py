import sys
from retrieve import retrieve


LOCAL_TOPIC_ANSWERS = {
    "Data, Models, and Learning": (
        "Data is the foundation of machine learning. A model learns patterns from data "
        "and uses these patterns to make predictions or decisions. In OTML, learning is "
        "viewed as an optimization process where the model parameters are adjusted to improve performance."
    ),

    "Model Fitting and Error Measurement": (
        "Model fitting is the process of adjusting a machine learning model so that its predictions "
        "match the actual outputs as closely as possible. Error measurement tells us how far the predicted "
        "values are from the actual values using measures such as loss, accuracy, or mean squared error."
    ),

    "Empirical Risk Minimization": (
        "Empirical Risk Minimization is a core principle in machine learning where the model is trained "
        "by minimizing the average loss on the available training data. It converts learning into an "
        "optimization problem because we define a loss function and try to find parameters that minimize it."
    ),

    "Parameter Estimation": (
        "Parameter estimation is the process of finding the best values of model parameters using training data. "
        "For example, in linear regression, the slope and intercept are estimated from data. In OTML, methods such "
        "as Least Squares Estimation, Maximum Likelihood Estimation, MAP, and gradient-based estimation are used."
    ),

    "Gradient Descent": (
        "Gradient Descent is an iterative optimization algorithm used to minimize a loss function. "
        "It updates model parameters step by step in the opposite direction of the gradient. "
        "The learning rate controls how large each update step is, and the process continues until the loss is reduced."
    ),

    "Lagrange Multipliers": (
        "Lagrange multipliers are used to solve constrained optimization problems. "
        "They help optimize an objective function while satisfying one or more constraints. "
        "In machine learning, this idea is useful when parameters or solutions must obey specific restrictions."
    ),

    "Convex Optimization": (
        "Convex optimization deals with optimization problems where the objective function and feasible region are convex. "
        "Its main advantage is that any local minimum is also a global minimum. "
        "This makes convex optimization highly useful in machine learning because the solution is reliable and easier to analyze."
    ),

    "Probabilistic Modelling and Inference": (
        "Probabilistic modelling represents uncertainty using probability distributions. "
        "Instead of giving only one fixed prediction, it estimates the likelihood of possible outcomes. "
        "Inference is the process of using known information to calculate unknown or hidden probabilities."
    ),

    "Directed Graphical Models": (
        "A Directed Graphical Model is a probabilistic model that represents variables as nodes and dependencies as directed edges. "
        "It is usually shown as a directed acyclic graph. In machine learning, it helps model conditional dependencies "
        "and supports inference over uncertain variables."
    ),
}


def make_short_answer(query, retrieved_results):
    if not retrieved_results:
        return {
            "answer": (
                "This topic is not covered in the provided OTML Module 1 "
                "and practical material."
            ),
            "sources": []
        }

    top_chunks = [chunk for score, chunk in retrieved_results[:3]]

    main_topic = top_chunks[0].get("topic_name", "")

    answer_text = LOCAL_TOPIC_ANSWERS.get(
        main_topic,
        "Relevant OTML material was found, but a clean local answer template is not yet available for this topic."
    )

    sources = []
    seen = set()

    for chunk in top_chunks:
        source_key = (
            chunk.get("source_file"),
            chunk.get("practical_no"),
            chunk.get("topic_name"),
        )

        if source_key in seen:
            continue

        seen.add(source_key)

        sources.append({
            "source_file": chunk.get("source_file"),
            "source_type": chunk.get("source_type"),
            "practical_no": chunk.get("practical_no"),
            "topic_name": chunk.get("topic_name"),
            "repository_url": chunk.get("repository_url"),
        })

    return {
        "answer": answer_text,
        "sources": sources
    }


def print_final_answer(query, result):
    print("\n============================================================")
    print("OTML STUDENT ASSISTANT - LOCAL ANSWER")
    print("============================================================")

    print("\nQuestion:")
    print(query)

    print("\nAnswer:")
    print(result["answer"])

    print("\nSources Used:")

    if not result["sources"]:
        print("No valid OTML source found.")
    else:
        for index, source in enumerate(result["sources"], start=1):
            print(f"\n{index}. {source['practical_no']} - {source['topic_name']}")
            print(f"   Source Type: {source['source_type']}")
            print(f"   Source File: {source['source_file']}")

            if source["repository_url"] != "Not applicable":
                print(f"   Repository: {source['repository_url']}")

    print("\nNote:")
    print(
        "This is a local template-based answer generated after retrieving OTML chunks. "
        "Gemini integration will be added later for more natural answers."
    )


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter your OTML question: ")

    retrieved_results = retrieve(query, top_k=3)
    result = make_short_answer(query, retrieved_results)
    print_final_answer(query, result)


if __name__ == "__main__":
    main()
from typing import List, Union, Dict, Optional, Tuple

import json
from haystack import BaseComponent, Document, MultiLabel
from transformers import AutoTokenizer, AutoModelForTokenClassification, TokenClassificationPipeline
from transformers import pipeline


class EntityExtractor(BaseComponent):
    """
    This node is used to extract entities out of documents.
    The most common use case for this would be as a named entity extractor.
    The default model used is dslim/bert-base-NER.
    This node can be placed in a querying pipeline to perform entity extraction on retrieved documents only,
    or it can be placed in an indexing pipeline so that all documents in the document store have extracted entities.
    The entities extracted by this Node will populate Document.entities
    """
    outgoing_edges = 1

    def __init__(self,
                 model_name_or_path="dslim/bert-base-NER"):
        
        tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        token_classifier = AutoModelForTokenClassification.from_pretrained(model_name_or_path)
        self.model = pipeline("ner", model=token_classifier, tokenizer=tokenizer, aggregation_strategy="simple")

    def run(self, documents: Optional[Union[List[Document], List[dict]]] = None) -> Tuple[Dict, str]:  # type: ignore
        """
        This is the method called when this node is used in a pipeline
        """
        if documents:
            for doc in documents:
                # In a querying pipeline, doc is a haystack.schema.Document object
                try:
                    doc.meta["entities"] = self.extract(doc.content)  # type: ignore
                # In an indexing pipeline, doc is a dictionary
                except AttributeError:
                    doc["meta"]["entities"] = self.extract(doc["content"])  # type: ignore
        output = {"documents": documents}
        return output, "output_1"

    def extract(self, text):
        """
        This function can be called to perform entity extraction when using the node in isolation.
        """
        entities = self.model(text)
        return entities


def simplify_ner_for_qa(output): 
    """
    Returns a simplified version of the output dictionary
    with the following structure:
    [
        { 
            answer: { ... }
            entities: [ { ... }, {} ]
        }
    ]
    The entities included are only the ones that overlap with
    the answer itself.
    """
    compact_output = []
    for answer in output["answers"]:

        entities = []
        for entity in answer.meta["entities"]:
            if entity["start"] >= answer.offsets_in_document[0].start and entity["end"] <= answer.offsets_in_document[0].end:
                entities.append(entity["word"])  

        compact_output.append({
            "answer": answer.answer,
            "entities": entities
        })
    return compact_output

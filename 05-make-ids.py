"""
Replaces the ids of the facts by YAGO ids

(c) 2022 Fabian M. Suchanek

Input:
- 04-yago-facts-to-rename.tsv
- 04-yago-ids.tsv
- 04-yago-bad-classes.tsv

Output:
- 05-yago-final-wikipedia.tsv
- 05-yago-final-beyond-wikipedia.tsv
- 05-yago-final-meta.tsv
- 05-yago-final-taxonomy.tsv

Algorithm:
- load yago-ids.tsv
- run through yago-facts-to-rename.tsv
  - replace the Wikidata ids by YAGO ids
  - write out the facts to the output files
   
"""

TEST=False
FOLDER="test-data/05-make-ids/" if TEST else "yago-data/"

##########################################################################
#             Booting
##########################################################################

import sys
import evaluator
import TsvUtils

##########################################################################
#             Helper methods
##########################################################################

def isLiteral(entity):
    """ TRUE for literals and external URLs """
    return entity.startswith('"') or entity.startswith('<http://') or entity.startswith('<https://')

def isGeneric(entity):
    """ TRUE for generic instances """
    return entity.startswith('_:')

def toYagoEntity(entity):
    """ Translates an entity to a YAGO entity, passes through literals, returns NONE otherwise """
    if entity.startswith('"'):
        return entity
    if entity.startswith('<http://') or entity.startswith('<https://'):
        return entity
    if entity.startswith("yago:") or entity.startswith("schema:") or entity.startswith("rdfs:") :
        return entity
    if entity.startswith("_:"):
        # Anonymous members of lists etc.
        if not entity.endswith("_generic_instance"):
            return entity
        # Generic instances
        cls=entity[2:-17]
        cls=yagoIds.get(cls, None)
        if cls==None or cls.find(":")==-1:
            return None
        return cls+"_generic_instance"
    if entity in yagoIds:
        return yagoIds[entity]
    return None
    
def goesToWikipediaVersion(entity):
    """ TRUE if the entity is a literal or has a Wikipedia page or is a generic instance"""
    return isLiteral(entity) or entity in entitiesWithWikipediaPage or entity.endswith("_generic_instance")
    
##########################################################################
#             Main
##########################################################################

with TsvUtils.Timer("Step 05: Renaming YAGO entities"):

    yagoIds={}
    entitiesWithWikipediaPage=set()
    for split in TsvUtils.tsvTuples(FOLDER+"04-yago-ids.tsv", "  Loading YAGO ids"):
        if len(split)<4:
            continue
        yagoIds[split[0]]=split[2]
        if split[3]==". #WIKI":
            entitiesWithWikipediaPage.add(split[2])
    
    for split in TsvUtils.tsvTuples(FOLDER+"04-yago-bad-classes.tsv", "  Removing bad YAGO classes"):
        yagoIds.pop(split[0], None)

    with TsvUtils.TsvFileWriter(FOLDER+"05-yago-final-meta.tsv") as metaFacts:
        with TsvUtils.TsvFileWriter(FOLDER+"05-yago-final-beyond-wikipedia.tsv") as fullFacts:
            with TsvUtils.TsvFileWriter(FOLDER+"05-yago-final-wikipedia.tsv") as wikipediaFacts:
                previousEntity="Elvis"
                for split in TsvUtils.tsvTuples(FOLDER+"04-yago-facts-to-rename.tsv", "  Renaming"):
                    if len(split)<3:
                        continue
                    subject=toYagoEntity(split[0])
                    if not subject:
                        # Should not happen
                        continue
                    relation=split[1]
                    object=toYagoEntity(split[2])
                    if not object:
                        # Should not happen
                        continue
                    # Write facts to Wikipedia version of YAGO
                    if goesToWikipediaVersion(subject) and (relation=="rdf:type" or goesToWikipediaVersion(object)):
                        wikipediaFacts.writeFact(subject, relation, object)
                        if subject!=previousEntity and split[0] in yagoIds:
                           wikipediaFacts.writeFact(subject, "owl:sameAs", split[0])
                    else:
                        fullFacts.writeFact(subject, relation, object)
                        if subject!=previousEntity and split[0] in yagoIds:
                           fullFacts.writeFact(subject, "owl:sameAs", split[0])                
                    # If there is a meta-fact, write it out as well
                    if len(split)>5:
                        if split[4]: metaFacts.write("<<", subject, relation, object, ">>", "schema:startDate", split[4])
                        if split[5]: metaFacts.write("<<", subject, relation, object, ">>", "schema:endDate", split[5])
                    if not subject.startswith("_:"):
                        previousEntity=subject
                    
    with TsvUtils.TsvFileWriter(FOLDER+"05-yago-final-taxonomy.tsv") as taxFacts:
        for split in TsvUtils.tsvTuples(FOLDER+"02-yago-taxonomy-to-rename.tsv", "  Renaming classes"):
            if len(split)<3:
                continue
            subject=toYagoEntity(split[0])
            if not subject:
                # Happens if a class has no label or no instances
                continue
            relation=split[1]
            object=split[2] if relation=="rdf:type" else toYagoEntity(split[2])
            if not object:
                # Happens if a class has no label or no instances
                continue
            # Write taxonomic fact
            taxFacts.writeFact(subject, relation, object)            

if TEST:
    evaluator.compare(FOLDER+"05-yago-final-wikipedia.tsv")
    evaluator.compare(FOLDER+"05-yago-final-beyond-wikipedia.tsv")
    evaluator.compare(FOLDER+"05-yago-final-meta.tsv")
    evaluator.compare(FOLDER+"05-yago-final-taxonomy.tsv")
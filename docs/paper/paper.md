---
title: 'CATS: The Climate Aware Task Scheduler'
tags:
  - Python
authors:
  - name: Andrew M. Walker
    orcid: 0000-0003-3121-3255
    affiliation: 1
#  - name: Author Without ORCID
#    equal-contrib: true # (This is how you can denote equal contributions between multiple authors)
#    affiliation: "1, 2" # (Multiple affiliations must be quoted)
#  - name: Author with no affiliation
#    corresponding: true # (This is how to denote the corresponding author)
#    equal-contrib: true
#   affiliation: 3
# - given-names: Ludwig
#   dropping-particle: van
#   surname: Beethoven
#   affiliation: 3
affiliations:
 - name: Department of Earth Sciences, University of Oxford, South Parks Road, Oxford, OX1 3AN UK
   index: 1
#- name: Institution Name, Country
#  index: 2
#- name: Independent Researcher, Country
#  index: 3
date: 27 November 2024

---

# Summary
The environmental impact of research computing is increasingly a topic of concern for researchers.
One of the main contributors of compute-related greenhouse gas emissions is the production of
electricity to power digital research infrastructures. The carbon footprint of electricity consumption 
(called carbon intensity), related to the energy mix (i.e. the share of renewable vs high-carbon 
production methods), varies greatly depending on time and location.  Here, we describe the Climate 
Aware Task Scheduler (CATS). CATS is designed to let researchers schedule computing when low-carbon 
electricity is available by using carbon intensity forecasts from the power supply network local to 
the computational resource they are using and thus reduce the climate cost of the computation. CATS 
also provides an assessment of the carbon savings due to delaying compute (vs compute happening now).

# Statement of need


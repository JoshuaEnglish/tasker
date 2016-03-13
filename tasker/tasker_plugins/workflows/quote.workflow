[Workflow]
name = Quote
description = Tasks related to creating quotes for HP TMs
vocabulary = project, TM

[Steps]
1 = (A) Log request for +$project @quote
2 = (B) Get complete information for +$project @quote
3 = (A) Submit approval for +$project @quote
4 = (A) Check for approval for +$project @quote
5 = (A) Send views to $TM for +$project @quote

[Instances]
1 = FourthProject,AllenM
2 = Fifth,Allen,Malarkey
3 = +HomeQuote,JeffZ


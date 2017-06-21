[Workflow]
name = Newhire
description = Planning Steps for new sales reps, sales engineers, sales directors, and VPs
vocabulary = person

[Steps]
1 = (A) Collect starting information on $person @newhire +${person}Hire
2 = (A) Confirm $person data in @DirectoryWorks @newhire +${person}Hire
3 = (A) Email Eric to set up $person in @SFDC @newhire +${person}Hire
4 = (A) Submit @TechDirect ticket to add $person in @Anaplan @newhire +${person}Hire
5 = (A) Submit ticket to add $person to @SFDC territories @newhire +${person}Hire
6 = (A) Put $person on guarantee in @Anaplan @newhire +${person}Hire
7 = (A) Send Jasjeet a summary of +${person}Hire @newhire
8 = (Z) Put $person on comp plan in @Anaplan @newhire +${person}Hire

[Instances]
1 = MattFleming
2 = KevinClark
3 = RichGreger
4 = JohnKlopacz


---
podcast: "The Innovation Show"
episode: "Understanding the Complexity of Modern Technology with Samuel Arbesman | Overcomplicated"
date: 2025-10-27
duration: "unknown"
url: "https://thethursdaythought.substack.com"
---

# Understanding the Complexity of Modern Technology with Samuel Arbesman | Overcomplicated — The Innovation Show

## Summary
Samuel Arbesman, author of *Overcomplicated Technology* and *The Magic of Code*, argues that modern systems—whether they are software, legal frameworks, or medical machinery—are reaching a state of incomprehensible complexity. The core thesis is that this complexity does not arise from single, brilliant design flaws, but rather from the continuous process of **accretion**: the slow, rational addition of features and decisions over time. This accumulation creates massive interconnected systems where even the original builders, or current experts, cannot fully grasp how they operate.

The discussion uses historical failures (like the 2015 NYSE suspension and the Toyota acceleration issues) to demonstrate that catastrophic system failure is often not due to a single "bug" but rather an inevitable result of building something massive without adhering to rigorous, comprehensive design practices. Arbesman posits that this systemic incomprehensibility creates a dangerous gap between how we *think* a system should operate and how it *actually* does.

## Key Points
- **The Danger of Accretion:** Complexity is not inherently bad; the problem arises when features are added as "good enough for now" placeholders, and these additions are never properly updated or fixed. This slow accumulation leads to massive, brittle systems that become essential but opaque (legacy systems).
- **Systemic Failure vs. Single Point of Failure:** We have a deep human desire to pinpoint a single cause ("the person who did something wrong"). However, in large, complex systems, failure is almost always the result of an *accumulation* of many small decisions and interconnected parts, making root-cause analysis nearly impossible.
- **The Knowledge Transfer Crisis (Legacy Code):** As systems grow, the original knowledge base—the "why" behind certain lines of code or legal clauses—is lost. This creates a situation where crucial components are maintained by people who have retired or passed away, leading to deep institutional vulnerability.
- **AI and the Ghost in the Machine:** The coming shift toward AI writing code exacerbates this problem. When machines write complex logic autonomously, the system moves further into the "ghost in the machine" territory—it performs actions that were never explicitly coded for by human hands, making prediction and control exponentially harder.

## Tools & Resources
- **Books:** *Overcomplicated Technology* (Samuel Arbesman), *The Magic of Code* (Samuel Arbesman)
- **Concept/Framework:** The concept of "Accretion" (understanding how systems grow through incremental additions).
- **Sponsor Mention:** Kyndryl (AI powered consulting for harnessing technology and competitive edge).

## Quotable
> "It's not always going to be, 'Okay, here's the single point of failure.' It's going to be rather, it is accumulation of a lot of things that lead us to this point of inevitability and incomprehensibility."
>
> "When we think about complex technologies, that is how they grow. People want to add features... each of those decisions by itself is quite rational."

## Action Items
- [ ] **Develop Systemic Thinking:** When analyzing a business process or technical project, shift focus from identifying the single point of failure (the person/bug) to mapping all points of *accrued* dependency and decision.
- [ ] **Mandate Knowledge Documentation:** Implement rigorous protocols for documenting "why" decisions were made in complex systems (code, legal policy, operational procedures), treating this documentation as critical intellectual property that must survive personnel turnover.
- [ ] **Audit Legacy Systems/Processes:** Identify the most essential but least understood parts of your current business infrastructure. Treat these areas as high-risk knowledge gaps and prioritize cross-training or external expert consultation to mitigate dependency on single individuals.
- [ ] **Study Complexity Theory:** Read material related to complex adaptive systems (CAS) to better understand how local, rational decisions can lead to global, unpredictable outcomes.

## Full Transcript

Before we start, I wanna thank our
sponsor Kyndryl, with a unique blend
of AI powered consulting, built
on unmatched service capability.
Kyndryl helps leaders harness the
power of technology for smarter
decisions, faster innovation,
and a lasting competitive edge.
You can find our friends at
Kyndryl at KYND R YL Kyndryl.com.
Why did the New York Stock
Exchange suspend trading without
warning on July 8th, 2015?
Why did certain Toyota vehicles
accelerate uncontrollably
against the will of the drivers?
Why does programming inside our airplanes
occasionally surprise its creators?
After a thorough analysis by top
experts, the answers still elude us.
We don't understand the software
running our cars or our iPhones or
our smartphones, but here's a secret.
Neither do the geniuses at
Apple or the Phds at Toyota.
Well, not perfectly anyway.
No one, not lawyers, doctors,
accountants, or policymakers fully
grasps the rules, governing our tax
returns, our retirement accounts,
and our hospital medical machinery.
The same technology advances that have
simplified our lives have made the systems
governing our lives, incomprehensible,
unpredictable, and overcomplicated.
Today's guest offers us fresh,
insightful field guide to
living with complex technologies
that defy human comprehension.
It is a pleasure to welcome back the
author of Overcomplicated Technology
at the limits of comprehension.
Samuel Arbesman, welcome back to the show.
Thank you so much.
Great to have you back, man.
I have the Arbesman tome behind me.
There you can see two books
on the shelf behind me.
We've covered the Half-Life of Facts.
Brilliant episode.
Great feedback on that, Samuel.
And also this is Up Next and followed
by his latest book, the Magic of Code.
Next week, Sam, I thought we'd start
with your overview of the book.
So.
For those people who go TLDL , too
long, didn't listen, what's the main
point from the book Over complicated.
Yeah, I mean, so the main point is
that when we think about technologies,
obviously our technologies have
gotten more and more complex over
time, more and more interconnected.
And I feel like each of us recognize this.
We're like, , we don't understand
how our phones work or how various
other technologies work, but the
truth is it's that, that issue of.
Not understanding these technologies.
It's not just for the users.
It is increasingly for the people who
actually built these systems or even
just work with them and the experts who
work with 'em on a daily basis, that
these technologies are increasingly
incomprehensible due to the accretion over
time, the kind of interconnection of all
the different systems together yielding
all these unanticipated consequences.
And so we, yeah, we are increasingly
getting into this realm of
incomprehensible technologies.
thought about how.
You must have had a moment.
You know that character from The
Simpsons that goes, ha ha, that guy
where when COVID hit, we saw the
resilience and the complexity of so
many of our systems and the lack of
resilience of those systems as well.
And you wrote it before the COVID
pandemic, which I thought was, was
thought was an interesting one, but
I mentioned in the intro those three
instances, I thought we better cover
those because people will be coming on.
Well, what were they about?
I don't quite remember what happened in
the Stark Exchange in 2015, for example.
Yeah, so this was yeah.
So back, I guess now, 20 years ago the
the stock exchange had an issue where I
think like certain parts of it went down.
It was also a, it was actually
interesting where I think the New York
Stock Exchange went down alongside a
number of other, computational systems,
like right around the same time.
And people actually thought initially
that this was just some sort of
coordinated attack where like people,
it was like some sort of cyber attack.
And then it turns out upon further
examination, wasn't, just buggy code.
And it happened to be that like
when you have enough bugs and large
technologies, eventually you'll have
things that simultaneously go down.
And so yeah, this is, it was one of those
instances, and I don't remember the exact
details, but it was one of these things
where I think there was this simultaneous
failure, which is kind of crazy to
And the other one was the Toyota car.
And Toyota, they're a client of mine.
They're gonna hate me for, for bringing
this up, but it's quite interesting.
I find it quite interesting that.
Even these companies that we laud as
great innovators, become susceptible
to this, particularly as we move
more and more towards code and we
kind of see code as a science, but as
you show in the book, it's more akin
to complexity and biology at times.
Yeah.
So, I mean, right when we think
of cars, we think, oh, like it's
this big piece of machinery.
And it is, it's big and complex,
but it's also increasingly just a
huge computer program on wheels.
Like these are computers.
On wheels.
Like they, they have, I think depending on
the situation, like they can be like tens
of millions of lines of computer code.
Which is often used as a rough
proxy for complexity of code.
Which means of course when you have
that amount of computer code, it
is very difficult for any single
human to keep it all in their head.
And so what happened with Toyota
vehicles, this is back in I think like
the, maybe like 2008 timeframe, if I
remember correctly that people noticed
that occasionally certain Toyota
vehicles would accelerate, unexpectedly.
This is called un
unanticipated acceleration.
And then occasionally when these
cars would just un accelerate
uncontrollably they would crash.
And in certain cases,
actually people died.
It was actually a really serious issue.
And so there was a court case to
try to understand what was going on.
And it was one of these situations where.
From what I understand, it wasn't like
you could point to a single like line
of code of like this kind of thing is
actually the reason for the failure.
It was rather that when the system reaches
this level of complexity, in this case,
it sounds like they all, they actually
built a system in such a way that they did
not actually adhere to certain, I guess
like responsible kind of coding practices.
But it was a situation where when you
build something that big and don't
necessarily do it as well as you could
have, the incomprehensibility of these
technologies is almost inevitable.
And so it wasn't like, oh, you could
point to like, oh, this was the reason for
the failure or some other kind of thing.
It was just when you have a system this
large that's the inevitable result.
And I think.
This kind of speaks to also
just more broadly how we think
about failure in systems.
We want like, like there's this deep
seated human desire to say, okay,
here's the reason for the failure.
Here's the person that
did something wrong.
And sometimes we can actually do that.
But as these systems become bigger
and bigger, we often can't do that.
It's just it's an accumulation of
a lot of different decisions and
the accumulation of the increasing
complexity of the system, whether it's.
Software.
It could be some sort
of mechanical system.
It could be the combination
of lots of different things.
It could be even like a legal system.
We can talk about that as well.
That you get that there is this kind
of inevitable result of like, okay,
when these things get so big, you are
going to have reduced understanding.
And as a result, there's
going to be failures.
There's going to be bugs.
There's going to be a gap between how
we think the system actually should
operate and how it actually does operate.
And we often don't know this until
we see the failure and then we
can use that failure to better
understand what's actually going on.
And we can talk about how bugs can be kind
of, and failures can be used productively,
but it's it's a very weird sort of mindset
that we increasingly need to use when
we deal with these complex technologies,
which is that it's not always going to be
Okay, here's the single point of failure.
It's going to be rather, it is
accumulation of a lot of things
that lead us to this point of
inevitability and incomprehensibility.
I thought about again, how you
were ahead of the curve here with
understanding how, and this is a
very important term, how code or how
jargon, how the law system accretes.
So this term accretion is important
one, but ahead of the point
of where we are with ai, where
the AI is now coding itself.
So.
We know that concept of the ghost in the
machine where the, the machine will do
something that it wasn't even coded for.
And nobody exists anymore in the company
who wrote that originally line of code.
And it's like Frankenstein code
or as it's called, spaghetti
code that accretes over time.
And I mentioned this to a guy who works
in a, a long longtime veteran in telcos.
And he told me, he said, yeah, he
remembers at times looking for the
guy who wrote the original code.
And he's like, on anybody
know where Bob is?
And he goes, is Bob even still alive?
And he's like, Bob's like
87, like retired 20 years.
And they're like, Bob,
sorry about this man.
Do you remember that line of code?
And inevitably one person will
remember it, but that person
then passes on and there's nobody
handing that baton from one.
Generation to the next.
There's a whole lot of complexity
in there that we're not even
ready for at this point.
Where we're going to this jump to
now AI writing the code so there's
no even human hands on it anymore.
There's a lot in there, Sam, but
I think starting with the term
accretion, we can build on that and
bring back in the point you said
there about the law, the legal system.
Yeah.
And so accretion is simply just
this process of, of a system kind of
growing and pieces being added to it
a little bit over and over, over time.
And when we think about complex
technologies, that is how they grow.
People want to add features, they
want to add complexity, they want
to handle additional situations.
And the truth is, each of those
decisions by itself is quite rational.
You say, okay, here's the system as it is.
We want it to haKyndryle this new thing
or some new, some, I don't know, new
type of software or whatever it is.
And then you add some additional
feature and so it, it slowly
but surely accretes over time.
The problem is though well
one, sometimes you're just
putting things as placeholders.
So like things are like okay,
here's good enough for now.
And then of course it never gets
updated or it never gets modified or
fixed, and then suddenly you're just
adding more and more on top of it.
But then you end up with these
systems that are still essential
for getting things to work.
But right.
The people might be long
retired, they might be dead.
And so this is like legacy code legacy
systems where these things that are
very old or no longer being updated
or are no longer being fully under
understood, are still essential for
these systems to be run and Right.
Exactly.
And when you were talking about those
kinds of situations, I was talking to
someone who, he used to work at Los Alamos
National Labs, which is kinda like this
national lab where they do these large
scale com computational simulations
around like nuclear explosions.
And he said he would like
occasionally come across chunks
of code that would have comments
around it saying, do not touch this.
No one knows what it does.
And like, and it just, that is, and it
sounds horrifying and weird, but the truth
is that's probably much more the rule
rather than the exception where we just
have lots and lots of things that are
still necessary for the system to run.
But And yeah, it's because this slow
steady accretion of functionality and
additional features or whatever it is.
And then of course, then you
have, I mean, you're connecting
the system to another system.
So the newer thing is still
reliant on the older thing.
And then, yeah, you get this
massive amount of complexity.
And and then we can talk about this
more, but our brains are not designed to
handle this kind of thing, but especially
with the law, going back to what you
were saying about these legal systems,
we add after law or regulation after
regulation, each one might seem completely
rational and completely reasonable, but.
These different rules are all interacting
and they're often interacting in ways
that no one who is building this system,
whether it's a legal system, whether
it's a more tech, more traditional
technological system anticipated.
And so, yeah, then you get these
massive unanticipated consequences.
And yeah, it's like with the legacy
stuff, and you can see this kind of in
the lead up to the Y 2K situation where
people were not quite sure what was gonna
happen when the year 2000 rolled around.
'cause s 'cause the, a lot of
computer systems only held two
digits instead of four digits.
And so they would think it was
actually 1900 instead of the year 2000.
A lot of these systems were
developed seventies or whatever
earlier or a long time ago.
And yeah.
And they had to often bring people
out of retirement and say, okay,
like, help us figure out these things
because no one was around who had
actually built those systems any longer.
I thought we'd mentioned why that's
important and there's a piece I pulled
from the book here that this, we might
miss this, that we're at this point where
it's a digital economy and so much of
our infrastructure is dependent on code
or on a digital economy, and you said
The relationship between our human made
systems and the natural world means that
each of our actions now has even more
unexpected ramifications than ever before,
rippling not just to every corner of our
infrastructure, but to every corner of
the planet and sometimes even beyond.
The totality of our technology and
infrastructure is becoming the equivalent
of an enormously complicated vascular
system, both physical and digital that
pulls in the earth's raw materials
and emits roads, skyscrapers, large
populations and chemical effluent.
Our technological realm has accelerated
the metabolism of the earth and
done so in an extraordinarily
complicated dance of materials.
Even changing the glow
of the planet's surface.
Absolutely love that.
But there's a really important point
there, and I think this is a point that
we miss because we're so busy and we
have a shifting baseline of technology
that we just become accustomed to and
we're onto the next one then all of
a sudden, including the race to ai.
I thought you might share
some thoughts on that.
I think many of us have this
sense that like there's us,
there's humans, or there's nature,
and then there's technology.
And the truth is, first of all, throughout
history, humans have always been affecting
our environment in the world around us.
But at this point, increasingly
we are in this weird sort of like
co-evolutionary situation where we have
modified the world itself at this point
is this massive technological system.
And so the the writer Kevin Kelly, he
refers to, he talks about the technium,
the entire ecosystem of technology.
we are embedded within that.
And of course what that means is when
this thing is massively, massively complex
that we don't, and we're in it, but we
don't necessarily fully understand it.
And so the the computer scientist, Danny
Hillis has talked about this idea that
we've moved from the enlightenment when
we thought we could apply our rationale
to the world around us to understand it.
And of course that still pays a lot of
dividends and we should not discount that.
But we've moved increasingly to what
he refers to as the entanglement where
everything is so hopelessly interconnected
that we can no longer fully understand it.
And right when you think about these
sociotechnical technical systems.
Both our infrastructure, our
software, the code that runs all
these different kinds of things.
Logistical systems.
We were talking, you mentioned
before, with the pandemic.
All these things are these, it's a,
it's this massively complicated vascular
system that really is a technology.
It is this massive technology.
No one person has built this entire thing.
It's emerged in this very distributed kind
of way, but now we are forced to contend
with it and really try to understand it.
And in many ways we have to look to
it in the same way that and biologists
try to understand ecosystems.
We now have to understand our
technological ecosystem in order to really
understand how these things actually
work or sometimes increasingly don't work
You delve a little bit into
complexity, the science of.
Complexity and I thought it was important.
Not everybody understands the difference
between complicated and complex,
and you do give it a bit of time in
the book as well, but you use them
interchangeably, but they have different
meanings and you mentioned that kind
of Gordian knot of the entanglement.
I think it's worth explaining
that so everybody's on the
same page as we progress.
And to, to be clear, I think different
people might distinguish between
complicated and complex in different
sorts of ways, and certainly in the book
I do often use them interchangeably.
Especially also just due to the fact,
like if I use the exact same word over and
over, it would be very annoying to read.
So I have to have a little bit
of synonyms, but I do want to
distinguish between, right, in terms
of complication versus complexity.
I when thing is, when something
is complicated, it has, it might
have a lot of interconnected parts.
And so , I discuss it in the context
between, I, I think I use the example
of a whole bunch of buoys in the
water that are all interconnected.
And so you, you take all the buoys, you,
and there's like a whole bunch of ropes.
You throw 'em out, you throw 'em on
the dock or on the pier or whatever.
the interrelationships is very
complicated, like trying to see, okay, how
this one is connected to this other one.
it, it requires a lot of
explanation and like description
to understand what that is.
But that system is static.
It's not, it doesn't have
sophisticated behavior.
It just has this very
convoluted structure.
a system is complex, not only does
it have a lot of parts, but, due to
the interactions of those parts, it
yields a whole set of behaviors that
are, that require sort of a different
mode of thinking to understand.
So like if you took all those buoys.
all those different connections
and then threw them in the water.
And then now with waves and things like
that, you now suddenly have feedback.
You might have some sort of weird emergent
behavior where they all move together in
a way that you couldn't fully anticipate.
And so those kinds of like non-linear
feedback and emergence and maybe
some sort of concerted behavior.
It's the behavior coupled with the
interactions and the connections that is
the sort of comp the kind of complexity
and complex things that I'm talking about
here and of course all these systems
that we were talking about so far.
not just complicated in terms
of, oh, like this is a really
hard thing to keep in my mind.
They are also in, they're also very
complex because not only do I need
to keep the bits and pieces in my
mind, I need to understand how they
all interact and then how those
interactions yield other interactions.
Then of course, you have a second
order thinking and third order, and
it becomes this weird non-linear,
highly complex process and behaviour
There's a book I'm reading
as well, I can't see it here.
I thought I had it.
It's called human Errors by Nathan Lents.
And it's about all these errors
we have in our genome and as
humans, you know, having a tailbone
that's no longer needed anymore.
And you do touch on this later on that
just as nature has that as we have
junk, DNA, that we think is junk, we
don't know actually quite what it does.
It could be very valuable that we
don't know what it does at all.
That this happens in code as well,
which I thought was remarkable,
that somebody might go, don't, you
can't remove that line of code.
You might be trying to clean up
the spaghetti code, but it does
something and it will have a
knock on effect like the buoy.
That's really important to understand
because people go, well, why
don't we just start from scratch?
And you're like, eh, it's not that easy.
Yeah.
And so this is this idea of like the
Kluge, which is like this thing like you.
build a system, it works.
But oftentimes you're building in certain
parts in a way that are not always the
cleanest or where like things work.
But as you try to actually interrogate
the system, you realize that these
things that you think maybe are not
as relevant are actually incredibly
vital for the system to operate.
And so, yeah, and especially within
software going back to like this accretion
process, like these things that you might
think are old or no longer relevant are
actually still vital for the system to
operate even if you don't necessarily
fully understand them and Right.
And like in terms of like
evolution, We have many things
in our evolutionary history.
Like we look at ourselves like we
are the like we are the cumulation of
many things that maybe are no longer
quite relevant but are still there.
They might be relevant, they might not be.
But we have to recognize
that kind of thing.
And so I think I mentioned the example in
the book of when so where we used to live
the backyard, there were these trees that
had these giant spikes on them, basically.
Like they were kind, kind of,
frightening
Honey Locust
I think it was honey
does Honey locust.
Yeah.
And yeah, the honey locust tree.
And so it turns out and I was doing
a little digging into why, there are
these spikes and biologists think that
the reason they're there is was to
actually prevent the giant megafauna
of North America from eating the leaves
or eating the fruit or whatever of
the tree, or eating the bark, maybe.
I don't know what it was.
But of course, these giant  megafauna,
like these, like massive sloths or
whatever, like they've been extinct
for tens of thousands of years.
But I mean, but evolution takes time and
so these trees haven't gotten the message.
So that kind of thing is still part of
the genetic information of of the tree,
even though it's no longer relevant.
And of course you see this kind of
thing with with code and technology more
broadly where it's just like these things
accumulate, they're maybe not relevant,
maybe they are, we don't really know.
Yeah.
And of course, yeah, going with like
junk, DNA, we now realize that like a
lot of that is not actually junk, but
systems, they have all these kind of
accumulations of things, bits and pieces.
There's been optimization processes that
we're not fully under, fully clear on.
And as a result, yeah, you
end up with these things.
You don't fully understand them.
They be klugy, they kind of work.
We don't really know.
And this is actually one of the, so
one of the other features of a lot of
these technologies we've talked about
accretion and interconnection, one of
the other forces that kind of causes
these systems to become very complex.
Is the idea of contending with
edge cases and kind of the
weirdness of the world itself.
The evolutionary process with within
biology will add bits and pieces to
handle, oh, this situation or this other
exception, or this other kind of thing.
It will not necessarily result in
something beautiful or pristine or clean
or optimize or we'll say it might be
optimized, but it might also, it might
not necessarily be a kind of like a simple
elegant kind of result, but it works.
It gets the job done.
And the same kind of thing happens in
technology where, especially when you're
dealing with the messiness of the real
world, especially the messiness of
the human made, real world, you have
to contend with all these edge cases.
And as a result, you end up
with a very complex system.
And so I give the example of like
building a calendar application.
Where like you would think, oh,
it's like very easy, like I'm
gonna build a calendar app, it's
gonna have 365 days in a year done.
And of course that's not quite true.
To actually handle our current Gregorian
calendar, you have to realize, okay,
not only are there leap years, which are
not every four years, they're actually
like it's every four years on, unless
it's every a hundred years, which is
also not divisible by every 400 years.
Then you have to, which is like a weird
kind of algorithm you have to include,
then you have to deal with maybe time
changes and the weirdness of time zones
and all these other kind of things.
And then suddenly you end up with
this massively complex piece of
software because it's dealing with
all of these weird, messy edge
cases of reality and to solve it.
Yeah, you would think, okay, maybe I can
make some like very clear algorithm, but
no, you often have to just put lots of
like weird if statements and other kinds
of things and it gets all very, very
complex and hard to understand as well.
I love that when you talked about
the edge cases, I heard one which was
incredible, which was self-driving cars
that once the self-driving car didn't
know what to do because a truck went
past full of traffic lights, transporting
them from one place to the next and the
car was like going it was not compute.
Explodes, it didn't
:).
Oh, I love that.
Yeah.
And then like, yeah, like finding these
edge cases and these things right.
, They're often super interesting
and I feel like with a lot of, and
ai, like the current AI systems.
And the interesting like thing is with
this, with the book over complicated, so
it came out in 2016 before the current big
wave of complex LLMs, but increasingly.
The way we begin to understand these
LLMs is by finding yeah, these weird edge
cases and exceptions to understand, okay,
like how are these things actually doing?
What they're doing?
How are they actually
processing information?
And and actually anyway, we'll discuss
this next week, but like the magic
code actually to discuss a lot of
these things around edge cases and
glitches and using these as windows
to understand our systems much more.
But oftentimes, right, you have
to haKyndryle the edge cases, then
you also increasingly realize that
oftentimes you have not haKyndryled
all the edge cases, but you don't
realize this until yet another edge
case comes to the floor and you're
like, oh my God, I hadn't realized this.
And I believe I discussed this idea
it's a term from physics, this idea of
a system that is robust, yet fragile.
And the idea behind this and maybe
I'm using the term a little bit more
metaphorically, but when a system is
robust, yet fragile, it means that
it's robust to all the things that we
anticipate it being able to handle,
but incredibly fragile to basically
anything outside of that distribution.
Outside of any of the things that
we've built the system to handle.
And, and is though, is we often don't
realize that a system is robust, yet
fragile until we are confronted with that
fragility until some bug creates some sort
of catastrophic cascade or whatever it is.
And of course, we see these things
more and more with where it's yeah,
some weird buggy version of windows or
some weird update, like causes weird
cascading suddenly, all the airlines
have gone down for like several hours
and we see these kinds of things
like they happen not infrequently.
And yeah.
And it's it's very
humbling.
that intellectual humility
is the common thread I see
through the three books in that.
That's where it starts from.
And then you just bring
it into different realms.
So you bring it from actual facts
and knowledge into the digital realm.
And then you go into the code
realm next, which we'll talk
about next week, which is nice.
And it's great.
That's why I love doing these series like
this back to back because it's a privilege
to get an author like this, to to do it,
but also to see the progression of their
thinking over time, which is really nice.
But there was a couple of things.
When you talked about the
complexity, the buoys tied together,
I thought about, well, that's
really important to understand.
You said, for example, a piece of
code goes down over here, it doesn't
seem like a big deal, but then
something over here doesn't work.
You talked about Gmail, for example,
happened Gmail, and they were like,
oh, what the heck's happening here?
And it was connected to some cloud
that they, somebody coded it for that
didn't, shouldn't have been to, so
there's all this klugy code or spaghetti
code in there and those people move on,
maybe hired somewhere else, et cetera.
But then there's the world
where you build upon that.
So you go the world opening up APIs,
the interoperability of code seems
like a great thing, which it is.
It needs to be accessible so it
can connect to everything else, but
there's a huge cost there and there's
a trade off with cost and Failure.
And again, these are things we
don't really stop to think about.
And why I like the book is that you, it's
stuff that you just wouldn't think of.
And as you said, until it happens, you,
and we don't actually foresee this.
We don't scenario plan, we
don't red team, we don't chaos
monkey like Netflix would do.
So maybe we'll talk about the
interoperability and that trade off.
This is one of those things
where on the one hand, building
systems that are interoperable,
sounds like a, an alloyed good.
Like you, oh yeah, you
want this kind of thing.
Like you want systems to be able to pass
information and update in certain ways.
And, that's great.
But of course it come, it does come with
trade offs as you mentioned, which is
that when one system maybe does something
wrong or one system is updated in a way
that the other system can't anticipate,
can have things that, that then cascade
through a system and cause failures
that you might not have recognized,
like inter, so interoperability, right?
These kinds of things always come
with trade-offs and and that's fine.
And I think for me, like going back to
the intellectual humility, it's more
just a matter of recognizing that when we
build our systems, we have to recognize
that it's going to come with trade-offs.
These systems might be more
sophisticated, but also as a result,
they might be more conducive to failure.
And so, and you mentioned like , the
cast monkey system within Netflix, way it
operates is actually trying to actually
reduce the amount of unexpectedness and
lack of understanding there, because
oftentimes when these systems go down,
you're not gonna fully understand
the entire shape of the system.
So really the best way to sometimes
understand how these systems actually
should operate is to, in this
case, , almost like inject bugs,
inject failures into the system.
And so the way the Chaos Monkey
system within Netflix works is it like
periodically just will, randomly take down
different subsystems to make sure that
when there is some unexpected failure,
the system is as robust as possible.
So the engineers are able to
actually build in a certain amount
of resilience and robustness.
But , when we have this kind
of interoperability, it also
highlights, two interesting things.
One is the fact that sometimes, going
back to what we were saying earlier,
like for failure is not a person.
It's not, oh, someone did something wrong.
It's more these two things, which on
their own can behave perfectly fine.
When they interact, there are going
to be unexpected consequences.
And so maybe you could say, oh,
then it's the fault of the person
who created the interconnection.
And of course, I'm sure , you can always
place blame, but you we also have to
recognize that to a certain degree,
these are systemic kind of failures.
They're not just like individual
choices that are causing these failures.
The other aspect of these systems and
in terms of like the interoperability
is actually also related to somewhat
how we think about open source software.
And I discussed this a little bit
more in my next book as well, but
oftentimes we think, oh, like you're
building on open source software.
A lot of people have been looking at it.
It should be really well understood.
And and sometimes that is true, but
many times systems that we think are
really well understood they're actually
integral for lots of other systems, like
the piece of open source software, but
it might be, it might not be maintained
by, I dunno, thousands of people.
It's maintained by one guy who's he
doesn't have enough time to haKyndryle
these kinds of things, or he built it
and then moved on to something else.
But it's still essential for a
lot of these other systems and.
see this where there was what was it?
The the heart bleed bug.
I think that might have been the one
that I mentioned where it was like,
it was one of these failures where
it turned out it was like something
related to the internet infrastructure.
And it was like, yeah, this one little bit
of code or this piece of software that was
essential for all these different things.
And it was like this one guy built
it a long time ago and it propagated.
And for me, actually, one of the
takeaways there I think is to also
just realize that we need to really
just invest more into like maintenance
and support for these kinds of things.
If they are essential and if they're
being used by all these different systems
and like they're then we should really.
Actually them in a way that kind of
befits 'em, like all the companies
that maybe use these kinds of things
should actually pay it forward.
Or actually this could pay it back.
Like actually allow these systems
to be maintained properly.
But overall, I would just say the
interoperability kind of goes hand in hand
with this intellectual humility of like,
yeah, when these things interconnect our
understanding is going to be reduced.
It doesn't necessarily therefore mean that
we don't understand it entirely or at all.
And we can talk about this more
about understanding is really
this kind of like spectrum.
It's not like an either like
full understanding or nothing.
But we have to recognize that as these
systems become more interoperable
or just increasing in size and are
built over time, our understanding is
going to be reduced., And that's fine.
We just need to confront
that with, with open eyes.
And it brings us, then you teed us
up earlier on to the idea of the
biological limits of human comprehension.
So whether we like to admit
that or not, it is very true.
We have limits and one of the
things that's been bugging me like
a buzzing fridge is the idea that.
It's gonna get worse the more
we outsource to the machine.
So digital dementia, where we do
more and more of our thinking.
If you get ChatGPT to write for you and
you're not going through the struggle
of the writing, you're not using
that muscle, that muscle atrophies,
that brain atrophies, et cetera.
But you say, as our systems become more
complex over time a gap begins to grow
between the structure of these complex
systems and what our brains can handle,
whether it's the entirety of the internet
or other large pieces of infrastructure.
Understanding the whole is no longer
even close to possible and hand in
hand with this becomes what happened
post-industrial revolution of our drive
towards specialization and the lack
there of, of T workers or generalists.
Yeah.
And so starting with kinda like
the biological limits of like
our ability to understand, right?
These systems, the way we build
these systems is based on right,
huge number of interconnected parts.
They're all doing things.
They're, there's feedback,
there's nonlinear phenomena.
These are not things that
we evolved to think about.
And, the truth is very
quickly our brains break down.
And I think I actually even discussed
like a whole bunch of different examples
of the things our brains are good at,
the things that computers can handle.
And so, yeah, like and there's like
a classic paper looking at like how
much, like how many bits of information
we can hold in our short-term memory.
And it's not hundreds or thousands,
which of course is still much
smaller than these systems.
It's seven like plus or minus two.
And so like.
that shows we are very limited.
The speed of our neurons
is , not particularly fast.
There's different estimates about
like how much we can actually
hold in our long-term memory.
So that actually might
be reasonably powerful.
But especially if you look at being
able to hold, I was mentioning
before, like these like nonlinear
feedback kinds of things.
Like these are things where systems
are feeding back on themselves.
There's all that's related to this
idea of like recursion where something
is calling itself and building
things more and more complicated.
also occurs in language where you can
say like I thought that she thought
that, he thought that I thought
like about this, or whatever it is.
And of course you can't do that more
than a few times before your kind of
brain breaks down in terms of trying
to understand a sentence like that.
A computer ha should have no issue with
actually parsing that kind of sentence.
And so you can see that once you
have multiple different layers of
feedback our brains are not good
at that, but these systems can keep
on doing these kinds of things.
And I think there needs to
be a recognition, right?
That we are building these
systems in a way that we are not
particularly good at understanding.
Now the question becomes
what do we do with that?
Like how do we still try to
understand these systems?
And this kind of goes to what we were
talking in terms of understanding, like
understanding is not a binary condition.
It's not okay.
I either understand this thing
with perfect, like perfect
fidelity and understanding every
aspect of it, or I'm living in
complete and total utter ignorance.
You can be somewhere in between.
And in fact, of our lives of understanding
things, that's where that's where we are.
And I think trying to figure out how we
can move close, like closer to the more
complete understanding and away from
the complete utter ignorance the key.
And so whether or not it's like
saying, okay, I have I can understand
how this module connects to this
other piece, or I can understand the
broader shape of what's going on.
That can be helpful.
Going back anymore.
You were talking about with AI of
like, on the one hand, you're right,
it's like reducing our understanding
of these kinds of things and maybe
we're no longer thinking about them.
That being said, think going back to
trade-offs if we say to ourselves,
okay, we will never understand these
systems, but can I use tools to better
understand the underlying technology?
So it's one of these weird things
where on the one hand , I don't
understand this technology.
But then I'm gonna use another
technology to actually understand
the original technology.
And that also comes with
trade-offs because maybe you'll
get an incomplete understanding.
Maybe the technology you're
using as a tool, of this like
technological microscope itself,
you might not fully understand.
And so there's always
going to be trade offs.
But I do think.
can sometimes use these tools,
these additional technologies,
to move us a little bit closer
to more complete understanding.
We might not ever get there, but
we can do these kinds of things.
And so one of the examples I give
this is like well before our current
era of AI was I think Google wanted
to better understand the energy
efficiency of their data centers.
And they used what was then probably
reasonably complex machine learning
what probably now is like extremely
rudimentary, but they recognized
that they were using this technique
to actually understand the systems
that they themselves could not
fully and completely understand.
And that's fine.
and I think that can
actually be very useful.
Oftentimes though when we build
these systems or build a mental model
for these things it's going to be a
simplification of the overall system.
The question becomes how
useful is that model?
Which is actually one of the things
I also discussed in the magic of
code about, like thinking about
complexity and managing complexity.
But yeah, this is one of those, one of
those things where I think we have to
recognize that like the technologies
we already have, like they're not,
it's not like, oh, we are increasingly
going to get to the point where we're
not gonna understand these technologies
and we have to grapple with that fact.
have been there for a long time.
the problem though is for many
of us, especially if you're not
dealing with these systems on a
daily basis, you've been shielded
from that level of complexity.
And I don't think I included this in
overcomplicated, but it was around the
time when the Apple Watch first came out.
There was this article in the it was in
the Wall Street Journal, I think like the
style section talking about, okay, are
people still gonna buy mechanical watches?
Are, is everyone just gonna
start buying smart watches?
And they interviewed this one guy who was
a big fan of mechanical watches and of
course there people are still buying them.
And he said, yeah, of course
I want a mechanical watch.
Like I think about a mechanical
watch it and all of its
sophistication, it's so wonderful.
As opposed to the smartwatch,
which is just a chip now.
Like I will not deny that a mechanical
watch is sophisticated, but like a
smart, like a chip, a smartwatch is
like, it's orders of magnitude more
complex than a mechanical watch.
But for many people they're shielded
from that level of complexity.
one of the things that I actually try
to argue for is like finding ways to
peek under the hood to actually kinda
reveal a little bit of that complexity
because increasingly we are being
shielded from these kinds of things.
Like you look at like an iPad which
is just like, I don't even know
how the files are stored versus
you look at like early computers.
, Like my family's first computer
was the Commodore Vic 20
connected to your television.
Used these like cassette tapes to
store information and the way you got
computer programs is like, oftentimes
you just enter the code in yourself.
And, I have vague memories of my
father doing this kind of thing.
And you could see the clear relationship
between the code being entered, like the
text being entered and what was happening
on the screen, sometimes resulting in a
game or something cool more often than
not, some weird buggy thing or whatever.
And you could see that
clear relationship and.
And I think for many of us though, we've
been shielded from that kind of thing.
And so one of the things I argue
is like finding ways to at least
reveal a tiny bit of that complexity.
'cause otherwise going to think,
oh, this thing is actually really
simple until some failure or some
cascading catastrophic issue.
And then we're confronted with
the fact that, oh no, this systems
are actually much more complex
than we might have realized.
often.
Even on as a reality thing that, you know,
what, what we see colors and all that.
It's just an interpretation
by the lens we have.
And you, you mentioned it as well,
and I went down a rabbit hole of
looking at , how technology actually
bolsters our level of understanding.
But one of the things I, found in
the history was we went from having
just two cones to trichromacy.
So we now were able to observe more
colors . But I often think about
that, the way we perceive things is
essentially like the desktop on a
computer versus the MS dos green writing.
It's just all these ones and
zeros on the screen, et cetera.
But we'll move on for that.
But the point I wanted to just lean on
there was the, that term abstraction,
which is, , I just assume that in a way
so I can just actually get on with it
that I can level up my understanding.
But I mentioned this that it became
even more apparent to me after our
last conversation and today was that.
The importance of using the
technology to actually level up.
Because of that limited, the magical
number seven plus or minus two, because
we have a limit in our understanding.
We can actually use the
technology to get above that.
So we don't have to hold all that in
working memory and we can then make
connections and patterns at a different
level that we couldn't make before.
And I think that's what technology
can do for us if we use it for that.
But one of the problems I have, and
I don't know if you've had this and
it's why I have that library behind
me and probably why you have it
is the burden of knowledge and the
burden of knowledge is a real thing.
Where, say for example, your
new book came out, right?
So I was like going, I cannot
interview him on his new book until
I've read his previous books to
see where he is coming from, right?
So I have it on the level of this
show, and that's why I cover older
books and people are like going,
oh, why are you covering that book?
And I'm go, well, I kind of need to
understand where that that theory
came from and if the person's still
with us, if they're still live,
definitely getting them on the show
to be able to bring those two things
together and to record that knowledge.
So you don't even have to read the book
anymore and you can maybe fast track
the burden of knowledge for yourself.
There's a lot in there, but I thought
that burden of knowledge thing is
important to understand and how
then tech can help us get over that.
Yeah, so this idea of the burden of
knowledge is right, like in order to,
and actually going, going back to the
scientific kind of stuff that we discussed
last week about the halflife of facts.
It's like oftentimes, like in order to
make discoveries at the frontier, you have
to learn everything up until that point.
There are things that have become
obsolete or there, I'm going
back to the halflife facts.
You don't necessarily have to learn,
like the cutting edge alchemy in order
to make chemistry discoveries, but you
have to learn a whole bunch and means
that it takes a long time and a lot of
training to really get to that frontier.
And, especially in science as we.
Learn more and more and our body of
scientific knowledge increases that
creates an increased burden to actually
learn all these different kinds of things.
And also in terms of our technologies,
like how we build these technologies also
requires a huge amount of understanding.
Like, especially as these technologies
get more and more complex, you have
to understand the bits and pieces of
different things and certainly the
framework that it was used in some
piece of software or whatever it was.
And abstraction can help with that
kind of thing, where you can say,
okay, here's the thing as it is.
I've abstracted away the details.
I don't necessarily have to worry about
everything that kind of came before it.
problem though is sometimes when
abstraction layers break down
and you actually are forced to
confront all, like all of those
kind of tho those pieces as well.
. And so, the burden of knowledge,
whether you're thinking about
technological advancement or
scientific advancement, Does, right?
It is this increasingly pressing
thing where it is harder and
harder to create new knowledge, new
technologies, whatever, because you're
often required to learn more and
more to get there at that frontier.
There are ways of sidestepping and going
back to this abstraction, but it is yeah,
it is a really big issue and then of
course it goes hand in hand with, there's
this increasing amount of knowledge
that's required or increasing amount of
understanding, our brains are finite.
Like, it's not like one of these things
where, okay, I can spend, a hundred years
understanding this kind of thing, or I
can absorb millions of pages of things.
Like you can't do that.
Like there either you don't
have enough time, you don't
have enough mental capacity.
It's just not possible.
And so, right then it becomes, can I use.
Tools, increasingly computational
tools and technologies to help me
grapple with the burden of knowledge.
Whether it's increasingly complex
technology or one that has lots of
different pieces together, whether
it's scientific knowledge and grappling
with different bits and pieces from
different sub fields or entirely
different fields to make new discoveries.
You need tools to , help you better
understand these kinds of things.
But as a result way that like, I want to
like peek under the hood, but sometimes we
feel like we're increasingly distant from
our technologies, you sometimes are, using
these kinds of things in a way that's
mediated by these assistive tools as
opposed to getting into the nitty gritty.
So there's always going to be
these sorts of trade-offs and we
just need to be open about them.
I mentioned there, the specialization,
and you touched on this, the idea of
being a generalist, that you have so
much knowledge, but actually when you
mentioned, for example, the Apple Watch,
just being a, oh, it's just a chip.
Well, it made me think of what you said
about the autonomous, or not even an
autonomous vehicle, but an electric
car, that it takes so many different
disciplines, different specialists
to come together and coordinate and
neurodiversity to see that same challenge
from different angles with different
specialties to bring it together in
order to develop that type of thing.
But oftentimes then to think about
that is very difficult when you
bring people, and they're all seeing
it from their own perspective, the
whole time, their own specialization.
But then the generalist, as you said, is
aware of all those different disciplines,
but also then able to zoom up above
them and see the common denominators,
the overlaps, the Venn diagrams
between all these different things.
But that is not very valued, but
extremely valuable in today's society.
I know I'm jumping a little bit ahead
here, but I thought it's an important
thing because I know many of our
listeners would be in that bucket and
would appreciate the shows, and, and
it's why I try and draw from different
elements, but there's common denominators
in all this stuff that is important for
innovation or change or transformation.
And going back to burden of knowledge,
like as you require huge amounts of
specialists to deal with these systems.
You require lots of expertise
and it requires a lot of effort.
The interesting thing about,
about these complex technologies
is exactly what you're saying.
They often draw on many, many
different areas of expertise.
And so there's huge amounts of
specialization involved, means
and large, no single expert can
haKyndryle all these different things.
And so then the question becomes, can
we actually gain a better sense of
understanding of these technologies?
And the, the key is, someone
who has a more kind of thinking.
Sometimes people call these like T-shaped
individuals where they might have a series
of expertise in one area, but that's
the vertical part of the T and then the
horizontal part of the T allows you to
jump across lots of different domains.
And whether that's being
able to more easily translate
different types of jargon.
Understanding exactly what you
were saying before of kinda like
mental models that can be useful
for multiple different domains.
I actually do think increasingly as our
technologies become interdisciplinary in
the different domains that they touch on,
we need these kinds of generalist thinkers
or these kinds of t-shaped individuals.
The problem though is
how do we create them?
How do we support them?
How do we kinda valorize them
in today's society where I think
expertise is often very, very valued.
Not to the detriment of generalists,
but it's very, very hard sometimes
to figure out how to cultivate them.
And David Epstein had a wonderful book
range where he tried to actually like
talk about the value and the power
of of people with more generalist
thinking and how to get these people,
build them and them in the world.
'cause I think we need more of them, but
especially when it comes right to building
these technologies we need more of them.
And actually, one of the things I
discuss is I remember my mother told
me about when she was in, what was it?
The Girl Scouts there were these
different badges you could get.
You could, I dunno, get a badge for
learning how to like go camping or who
knows, all these different, but then there
was one badge called the dabbler badge
and it was like getting like just doing
a little bit of lots of different things.
And she told me that she
earned the dabbler badge.
And it was like, and I love the fact
that like there was this reward or
there was this recognition of like,
knowing a little bit about lots of
different things is actually valuable.
That in itself is something that we need
to actually value and and recognize.
And I think.
Increasingly as a society, we have
to recognize like we need more
of these dabbler, we need people
who are like, we need dabbler
badges for these kinds of things.
'cause those are the kind of
generalists who they will need to
work in conjunction with experts.
It's not an either or.
It's not just, oh, we only need
experts, or we only need generalists.
But we have to recognize that cultivating
generalists as well as actually
inclu incorporating them into our
organizations is very, very valuable.
'cause oftentimes, like when you have
an organization that is just full of
experts, like they're dealing with
their very specific thing and there is
no one then in that organization that
has the luxury or the mandate to say,
oh, let's take a little step backward.
Let's figure out how these
things interconnect or
sometimes fail to interconnect.
Or are there other ideas
that we should be exploring?
Are there ideas that we can use
in this import export business of
knowledge that we can bring to bear?
And yeah.
So we need to find ways to actually
recognize, yeah, that this is a very
valuable part of knowledge creation,
of managing complex technologies.
As opposed to just saying, either there's
gonna be people who know everything
or there's gonna be people who are
experts in some very specific thing.
Like we need to build people
who have not knowing everything.
'cause then it's like a dilletent
'cause then they really actually
don't have any deep expertise.
So I think that t-shaped individual or so
where you actually do have an expertise,
but you are also very comfortable jumping
into lots of different domains and
then providing that sort of connective
tissue to different experts that is
something that we really need more
And just a note to our audience, David
Epstein will be on the show next year.
We're gonna be doing a version of the
Sam episode with him covering his books,
the Sports Gene and Range, and I think
he might be working on a new one in the
meantime, just like you did Sam, as well.
I'll have to, I have to code
in for an extra week there.
It's like the Y 2K code.
I'll have to make space for
an extra book for people.
But I was intrigued and I loved,
I absolutely loved what you talked
about, the difference between physics
thinking and biological thinking.
I absolutely loved this.
And the contrast of those and
the mirror of those within a.
Innovation.
In innovation literature, we talk about
the need for exploration and exploitation.
Much like you said, the girl guides
that type of roaming and exploring
versus being a soldier and very
focused on a certain challenge.
But that difference is beautiful and
I'd love you to take us through it.
Yeah.
So I'm sure there, there are gonna be
many physicists and biologists that
will view this as an oversimplification.
But the way to think about this
kind of thing is oftentimes the
physics mode of thing, whether or
not it's always physicists doing
this kind of thing, but the physics
mode of thinking involves like.
Going back to abstraction, abstracting
away the details, saying, okay,
this system is very complex.
But I can ignore certain details
and try to see, okay, here are the
broad shape of what's going on.
And that kind of thing is
really, really powerful to say.
Okay.
Like looking at the world and
saying, okay, throwing a ball the
way the moon orbits the earth.
The I don't know, the way the tides
work, like these things are all like
wildly different, it turns out we
can abstract away the details and say
they're actually all being involved.
Like they're, there's gravity,
like gravity is the thing
that kind of understands the
parabolic arc of a baseball.
And trying to help us explain
the tides, help us explain the
orbits of the planet, so the orbit
of the moon or whatever it is.
And this is incredibly powerful,
that kind of like new Newtonian
approach of saying, okay, here's all
these widely disparate phenomena.
Let's actually try to understand
them in some sort of unifying way,
this kind of unifying approach
that ignores certain details.
And I would say that's like
the physics mode of thinking.
The biological mode of
thinking is saying no.
In fact, sometimes we we need to
like revel in all the details because
the details are actually really,
really important to understand.
Okay.
What is like the specific evolutionary
history for how we got to where we are
and why this thing does this in biology?
And of course you can see both.
And I would say like the biological
mode of thinking in physics maybe is
like where people were just trying
to like collect lots and lots of
different particles when they're
like understanding particle physics.
That would be a more biological mode in
physics and in, and conversely the, a
physics mode in biology would be like.
Darwin and saying, okay, actually
evolution explains a whole host of
disparate things that we actually see.
being said, this kind of the detail
oriented mode, which is more akin
to collecting lots of different
bits of information and then
slowly but surely building up a
complete picture of what's going on.
That works really, really well when
you have a really sophisticated system
where the details actually matter.
And increasingly, those
are our technology.
Those are our technologies.
We think, okay, our technologies,
they are, they're human made.
They're going to be entirely rational.
And yeah, sometimes they are.
But when you have a really complex
technology that has an almost
organic level of complexity.
It's evolved over time.
We have legacy, like we're
actually using biological terms.
, And at that point it becomes, oh, maybe
we should actually use the techniques
of biological thinking or even the
way in which biologists interrogate
complex biological systems to actually
interrogate complex technologies.
And often when I give a talk about
overcomplicated and complex technologies
I'll show this massively complex chart.
It looks like a circuit diagram and
it turns out it is a diagram of the
metabolic processes within a cell.
So it is a biological system but
it looks like a complex technology.
And of course conversely complex
technology are increasingly
looking like biology.
And you see this actually with a lot
of AI systems where we understand
the general principles of how
these systems are trained, but
the result is incredibly complex.
And then it requires interrogating
them using almost like biological,
like field biology kind of principles
of weird exceptions why these
things do these weird situations.
Trying to slowly but surely build up a
picture of why these LLMS or other AI
systems are doing what they're doing.
Because oftentimes that is going to
be much more valuable than saying,
oh, like I'll just abstract the way
the details and this is how it works,
because that's not how it works.
In biological systems or at least
using the biological mode of thinking,
abstracting the way the details misses
so much of the system's behavior
that you can't actually a afford
to ignore those kinds of details.
I have a lovely quote, Sam, right at the
end of the book that I'd love to share.
And before I share that as our
final message, I'd love you to
think about your final message,
and , I hope this might tee you up.
Actually, it's beautifully written.
You said There is a whimsy and beauty
in the complicated and the unexpected.
A glittering and shimmering technological
network with its branching gossamer,
web of links and interactions is
unbelievable in its complexity.
And sometimes even if we don't
understand every part and every hole,
an imperfect grasp can be enough.
We can walk humbly with our technology.
I love that.
That was the end of chapter five, but
I just thought it was a nice finale
and beautifully written, but over to
you maybe as your final message for
this part two on overcomplicated.
Yeah.
Thank you.
Yeah, and I think Yeah, this message
of humility is one of the things that
I think a lot about, whether it's
understanding our science or technologies
that oftentimes, like going back to
what I was saying we're not gonna have
complete ignorance, we're not also
not gonna have complete understanding.
Our understanding is going
to be somewhere in between.
oftentimes when we are confronted
with technologies we don't fully
understand, often zoom to two extremes.
One of fear in the face of the
unknown, or awe in the face of this
thing is like so unbelievably complex.
It's almost like the mind of God.
And of course, like it's not the
mind of God, it's like the mind of, I
dunno, Google or like some other thing.
It's built by imperfect people.
And in the fear in the
face of the unknown.
Yeah, these systems can be complex,
but oftentimes both fear as well as
awe like this kind of undue reverence,
they cut off questioning and any
sort of attempt to fully or further
understand the system, what's going
on, we might never fully understand it,
but we need to actually keep on trying.
And so for me that kind of productive
middle ground is humility, which is
saying, okay, I might not f ever fully
understand these things and that's okay.
And actually I talk about how in the era
before the Enlightenment certainly in the
Middle Ages there was this understanding
of like, oh yeah, there are certain things
that humans might never fully understand.
And of course, with the advent of the
enlightenment, we set that aside and I
think that's, that is good, that we should
actually keep on trying to understand
our technologies aspects of the world.
These things are very, very important.
But we still might need to recognize
that yeah, there's going to be limits.
Humans are incredibly finite creatures
and so we should keep on trying to
understand things but also recognize
that it's okay if we don't fully
understand it in all of its details.
And so for me, as long as we have this
productive humility of never stop trying
to actually further understand our
technologies or the systems we built,
or aspects of the world around us,
but also recognize that we are going
to be finite and so we might need to
grapple with that kind of thing, then
I think we are going to be much better
positioned to actually engage with the
true complexity of the world around us
as opposed to saying like, oh no, this is
something we can never fully understand.
Or actually sometimes thinking that it's
actually a lot simpler than it truly is.
And so as long as we maintain that
productive humility in the face of
even the technologies we ourselves
have built, I think we'll be able to
build them better as well as try to
actually understand them more and more
productively.
And Sam, for people who want to
find you, your substack, your books,
et cetera, where's the best place?
Yeah, so the best place, if you go to
my website, Arbesman.net, that will
have links to my substack as well
as a lot of my writing and my books.
And that's probably the best way to
reach me.
author of Over Complicated
Samuel Arbesman.
And don't forget Up Next
Magic of Code next week.
Thank you for joining us.
Thank you so much.
Thanks again to our sponsor, Kyndryl.
With a unique blend of AI powered
consulting, built on unmatched
managed service capability.
Kyndryl helps leaders harness the
power of technology for smarter
decisions, faster innovation,
and a lasting competitive edge.
Find out more about Kyndryl
at K-Y-N-D-R-Y-L Kyndryl.com.

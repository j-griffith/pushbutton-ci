# pushbutton-ci

OpenStack CI that's *almost* push button launch and run

## Motivation

A while back this all started with sos-ci, but that got ugly after it grew for
a while and it became more difficult to deploy and use than I would've liked.

So, this takes some of the concepts and ideas of sos-ci and tries to simplify
things a bit by using a proper rabbit message que and by using docker.

The addition of docker-compose and Dockerfiles should hopefully make deployment
a snap, as well as extending.  One example is the addtion of subunit, I ran
into a number of problems when adding subunit because my Instnace wasn't really
set up or sized for things like added db and parsing things out clearly.  Sure,
that could've all be fixed, but why not just separate the components into
containers and allow users to mix/match or add more workers on demand.

The result is pushbutton-ci which is almost like providing the ability to
deploy and run an OpenStack third party CI system just by launching a single
docker-compose command.  To be fair, it's currently set up specifically for
Cinder, and there are some prereq steps that you need to do (populate a vars
file), but after that it's really pretty simple.

## Basic architecture

This is completely OpenStack-centric, in other words, we're assuming you're
running CI against an existing OpenStack cloud.  If you're using some other
cloud... well, this probably isn't the toolset for you.

For now we're setting this up by linking 3 containers each with their own
specific task.

1. RabbitMQ server
    Well, what to say here.. it's a RabbitMQ server

2. Handler server
    Handler doesn't do a ton, just logs in to the gerrit stream and picks of
    events, looking for the ones that it's interested in and wants to perform a
    CI run against.  If/When it catches a valid event, it just simply publishes
    it out on the Rabbit Queue

3. Operator server
    The heaviest weight component, purpose in life is to just pull events off
    the queue and run a series of CI related playbooks against said event

Note that the Ansible Playbooks we use here are a part of a subrepo, so you'll
need to be sure and do a `git submodule update --init` to pull those in.

We're using the excellent shade module to create/delete our Instances,
and we're using a local mountpoint that we pass into our containers to deliver
the needed executables, and provide persistence of things like log files and
results bundles.

## Scaling workers

Need more workers?  Just increment the number of operator's in the
docker-compose file and run compse again.

## Quick Start

`git clone https://github.com/j-griffith/pushbutton-ci`

`cd pushbutton-ci`

We're using the excellent shade module to create/delete instances, so
you'll need to modify the cloud.yaml file to point to your OpenStack cloud that
you want to use.

`vim operator/src/cloud.yaml`

Next up, modify the vars.yaml file to set all the vars we need for like Ansible
and stuff.

`vim operator/src/vars.yaml`

Ok.. so that wasn't too bad; now we can just use docker-compose to build our
images and launch things.  Note that rather than using pre-canned images I'm
adding a Dockerfile to let you see exactly what you're getting and build your
images locally.  The first time you run this it takes a few minutes, but after
your images are built and added to your registry it's like any other container
that starts up right away.

`docker-build`

Ok, that's the hardest part, now just run it...

`docker-compose up -d`



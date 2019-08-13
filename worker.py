from faktory import Worker


def workshop_update(wsid):
    print(wsid)


w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.run()
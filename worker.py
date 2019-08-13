from faktory import Worker


def workshop_update(id):
    print(id)


w = Worker()
w.register("UpdateWorkshop", workshop_update)
w.run()
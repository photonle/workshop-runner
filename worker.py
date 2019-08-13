from faktory import worker


def workshop_update(id):
    print(id)


w = Worker()
w.register("WorkshopUpdate", workshop_update)
def evaluate_score(correct_answers):
    if correct_answers <= 5:
        return "A1", "3.0"
    elif correct_answers <= 10:
        return "A2", "4.0"
    elif correct_answers <= 15:
        return "B1", "5.0"
    else:
        return "B2", "6.0"

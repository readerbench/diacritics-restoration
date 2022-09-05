from diacritics_restoration import DiacriticsRestoration


if __name__ == "__main__":
    model = DiacriticsRestoration()
    result = model.process_string("Iata un text fara diacritice. Oare reuseste modelul sa il corecteze?")
    print(result)
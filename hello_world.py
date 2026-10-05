import sys
from PySide6 import QtWidgets


class Formulaire(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Formulaire")

        self.nom = QtWidgets.QLineEdit()
        self.nom.setPlaceholderText("Votre nom")
        self.role = QtWidgets.QComboBox()
        self.role.addItems(["Enseignant", "Administratif", "Direction"])
        self.bouton = QtWidgets.QPushButton("Valider")
        self.resultat = QtWidgets.QLabel("")

        layout = QtWidgets.QFormLayout(self)
        layout.addRow("Nom :", self.nom)
        layout.addRow("Rôle :", self.role)
        layout.addRow(self.bouton)
        layout.addRow(self.resultat)

        self.bouton.clicked.connect(self.valider)

    def valider(self):
        self.resultat.setText(f"{self.nom.text()} - {self.role.currentText()}")


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    fenetre = Formulaire()
    fenetre.show()
    sys.exit(app.exec())
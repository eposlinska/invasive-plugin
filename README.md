# IAS Parcel Join

QGIS plugin (Poland only). Downloads occurrences of invasive alien species (IGO) from the General Directoriate for Environmental Protection (GDOŚ) WFS
and builds a per-commune report with the parcels (EGiB) where each species occurs.

Install: copy the `IASParcelJoin` folder to the QGIS profile `python/plugins` directory
(or zip it and use *Plugins → Manage and Install Plugins → Install from ZIP*).

Data: GDOŚ (inwazyjne.gdos.gov.pl), GUGiK PRG and EGiB WFS services.
Species lists and statuses are compiled from secondary sources and must be checked against the regulation (The list of invasive alien species that threat Poland or the Union) if the update appears.

Developed by Eva Poslinska with the assistance of Claude (Anthropic, model Claude Sonnet 5.5), which helped write and debug the code. The code of the plugin was written with AI assistance.  The performance and the results of the plugin were tested by Eva Poslinska and Dorota Twardzik against the verified information obtained from Central Registry for IAS in Poland.

Co-Authored-By: Claude <noreply@anthropic.com>

<p align="center">
  . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 
</p>

Wtyczka QGIS (do zastosowania wyłącznie w Polsce). Za pomocą wtyczki możesz pobrać warstwy interesującego Cię inwazyjnego gatunku obcego, który występuje w kontrolowanej przez Ciebie gminie. Dane pobierane są automatycznie z WFS udostępnionego przez GDOŚ oraz łączone z danymi EGiB. Również za pomocą wtyczki możesz wygenerować raport wszystkich stwierdzeń gatunków obcych w danej gminie, w zależności możesz wybrać gatunki szeroko rozprzestrzenione lub gatunki podlegające szybkiej eliminacji.

Instalacja: skopiuj folder invasive-plugin do profilu QGIS i umieść w katalogu 'python/plugins'.
Opcja 2: pobierz zip i dodaj wtyczkę za pomocą QGIS - _Wtyczki → Zarządzaj i instaluj wtyczki → instaluj z ZIP_
Opcja 3: zainstaluj wtyczkę z ogólnego źródła QGIS.

Dane: serwisy WFS GDOŚ (inwazyjne.gdos.gov.pl), GUGiK PRG i EGiB.
Lista gatunków została stworzona ręcznie, więc w przypadku aktualizacji rozporządzenia ws. listy inwazyjnych gatunków obcych stwarzających zagrożenie dla Polski lub stwarzających zagrożenie dla Unii konieczna będzie aktualizacja wtyczki.

Stworzone przez Evę Poślińską z asystą Claude (Anthropic, model Claude Sonnet 5.5), który pomógł w pisaniu oraz w diagnozowaniu błędów kodu. Kod wtyczki został napisany z asystą Sztucznej Inteligencji (AI). Działanie wtyczki zostało przetestowane przez Evę Poślińską i Dorotę Twardzik, a uzyskane w trakcie testów wyniki zweryfikowane z Centralnmym Rejestrem Danych o Inwazyjnych Gatunkach Obcych funkcjonującym w Polsce.


Napisana wspólnie przez: Eva Poslinska i Claude <noreply@anthropic.com>
<p align="center">
  <img src="IASParcelJoin/icon.png" alt="Icon">
</p> 

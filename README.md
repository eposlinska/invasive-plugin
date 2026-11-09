# IAS Parcel Join

QGIS plugin (Poland only). Downloads occurrences of invasive alien species (IGO) from the General Directoriate for Environmental Protection (GDOŚ) WFS
and builds a per-commune report with the parcels (EGiB) where each species occurs.

Install: copy the `IASParcelJoin` folder to the QGIS profile `python/plugins` directory
(or zip it and use *Plugins → Manage and Install Plugins → Install from ZIP*).

Data: GDOŚ (inwazyjne.gdos.gov.pl), GUGiK PRG and EGiB WFS services.
Species lists and statuses are compiled from secondary sources and must be checked against the regulation (The list of invasive alien species that threat Poland or the Union) if the update appears.

Developed by Eva Poslinska with the assistance of Claude (Anthropic, model Claude Sonnet 5.5), which helped write and debug the code.

Co-Authored-By: Claude <noreply@anthropic.com>

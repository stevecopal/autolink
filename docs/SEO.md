# Stratégie SEO — AutoLink (autolink.cohub.site)

> Document de travail : état des lieux technique, mots-clés cibles, plan de
> contenu, netlinking, procédures Search Console / Analytics, plan 30-60-90 et
> checklist avant indexation.

---

## 0. Cadrage important : le produit réel

Le brief initial décrivait AutoLink comme un **raccourcisseur d'URL / outil de
gestion de liens**. D'après le code de ce dépôt, la réalité est différente :

| Élément | Réalité constatée dans le code |
|---|---|
| Produit | **Marketplace automobile au Cameroun** : garages vérifiés + pièces détachées |
| Modèle | Les garages paient une **activation** (CamPay / Mobile Money) ; les clients sont gratuits |
| Fonctions | Recherche geolocalisée (`/a-proximite/`), fiches garages, catalogue de pièces, messagerie/tickets, espace garage, PWA hors ligne |
| Langue | `fr` par défaut (`en` déclaré mais **aucune traduction compilée**, pas d'URL préfixées) |
| Domaine | `autolink.cohub.site` (Caddy → `autolink_django:8000`, PostgreSQL, VPS Contabo) |

**Conséquence SEO majeure** : le site ne doit **pas** être optimisé sur
« raccourcisseur d'URL », « liens courts » ou « gestion de liens » — aucune
requête liée à ces sujets n'aboutira à une conversion, et le contenu indexé ne
correspondrait pas à la page de résultats. Le référencement doit cibler les
recherches **automobile Cameroun** (§2).

> « Autolink » reste un nom ambigu côté marque : la stratégie inclut donc un
> travail de brand (recouvrement de marque, Business Profile, cohérence NAP).

---

## 1. Ce qui est déjà livré dans le code (et vérifié)

| Livrable | Fichier | Vérification |
|---|---|---|
| `robots.txt` dynamique (URL sitemap auto) | `core/views/seo.py` + route dans `autolink/urls.py` | `curl -s https://autolink.cohub.site/robots.txt` |
| Sitemap XML dynamique (5 sections) | `core/sitemaps.py` + route `sitemap.xml` | `/sitemap.xml`, `/sitemap.xml?section=villes` |
| URL canonique + OG/Twitter + JSON-LD global | `templates/public/base.html` | `<link rel="canonical">`, `og:*`, `application/ld+json` |
| Aide SEO centralisée (URL publique, JSON-LD) | `core/seo.py` | — |
| Balises de données structurées | `core/templatetags/seo_tags.py` | AutoRepair, Product, BreadcrumbList, Organization, WebSite |
| Context processor SEO | `autolink/context_processors.py` | `SEO_CANONICAL`, `SEO_GOOGLE_*` disponibles partout |
| `noindex` sur les zones privées | `autolink/middleware.py` (en-tête `X-Robots-Tag`) | `/compte/`, `/admin/`, `/recherche/`, `*/api/` |
| Landing SEO par ville | `garages/views.py::garage_city_view` → `/garages/ville/<slug>/` | H1 = « Garages auto à Douala » |
| Canonical consolidé des filtres | `garage_list_view` → `seo_canonical` | `?city=douala` → canonical ville |
| Image OpenGraph 1200×630 | `manage.py build_og_image` → `static/og-image.jpg` | 22 Ko |
| Variables SEO | `.env` / `.env.example` : `PUBLIC_SITE_URL`, `GOOGLE_SITE_VERIFICATION`, `GOOGLE_ANALYTICS_ID` | — |
| Config proxy/CDN | `deploy/Caddyfile.autolink` | redirection www, cache, compression |

**Ce qui reste à faire côté technique** (détaillé §3) : finaliser la page
catégories, pages quartiers, blog/guides, `Site` Django (framework `sites`),
sitemap index si le volume dépasse 50 000 URLs, redirection des anciennes URLs
si elles changent.

---

## 2. Mots-clés cibles et intentions

Priorité = **intention locale + transactionnelle** (quelqu'un qui cherche un
garage ou une pièce maintenant). Volume faible par requête au Cameroun, mais
concurrence faible et conversion élevée.

| # | Requête cible | Intention | Page à positionner | Priorité |
|---|---|---|---|---|
| 1 | garage auto Douala | Locale transactionnelle | `/garages/ville/douala/` | ★★★ |
| 2 | garage mécanique Yaoundé | Locale transactionnelle | `/garages/ville/yaounde/` | ★★★ |
| 3 | mécanicien près de moi | Locale mobile | `/a-proximite/` | ★★★ |
| 4 | pièces détachées auto Cameroun | Transactionnelle | `/pieces/` | ★★★ |
| 5 | pièce auto Douala / Yaoundé | Transactionnelle locale | `/pieces/?city=…` → page ville pièces (à créer) | ★★ |
| 6 | garage vérifié Cameroun | Confiance | `/` + `/a-propos/` | ★★ |
| 7 | prix réparation auto Cameroun / prix vidange | Informationnelle → conversion | Guide « Prix des réparations au Cameroun » (à créer) | ★★ |
| 8 | vidange / diagnostic / carrosserie + ville | Locale | pages service × ville (à créer) | ★★ |
| 9 | pièces Toyota / Hyundai / Nissan Cameroun | Longue traîne produit | pages marque (à créer) | ★★ |
| 10 | comment choisir un bon mécanicien | Informationnelle | guide blog | ★ |
| 11 | ouvrir / gérer un garage au Cameroun | B2B (cœur du modèle) | page « Inscrire mon garage » | ★★★ |
| 12 | AutoLink Cameroun | Marque | `/` (+ Business Profile) | ★★★ |

**Méthode** : valider chaque liste avec Google Keyword Planner (compte Ads) et
la section **Requêtes** de Search Console dès les 4 premières semaines (les
données réelles de GSC sont plus fiables que tout outil tiers).

> Note outils : Ahrefs / SEMrush / Ubersuggest sont utiles mais coûteux ; les
> versions gratuites de GSC + Keyword Planner + les suggestions Google/YouTube
> suffisent au démarrage.

---

## 3. SEO on-page : règles et exemples prêts à l'emploi

### 3.1 Règles de rédaction

1. **Un `<title>` unique par page**, 50-60 caractères, mot-clé + lieu + marque.
2. **Une `meta description` unique**, 140-160 caractères, orientée bénéfice +
   appel à l'action (elle n'améliore pas le classement mais le CTR).
3. **Un seul `<h1>` par page**, contenant le mot-clé principal. Les `<h2>`
   structurent le contenu (services, horaires, quartiers, FAQ).
4. **Contenu utile minimum** : une page ville/quartier sans garage réel = page
   vide → elle ne doit pas être indexée. C'est implémenté : le sitemap ne liste
   que les villes ayant au moins un garage public, et la landing ville passe en
   `noindex` (tout en restant consultable) quand la ville est vide.
   Une ville inexistante renvoie un vrai **404** (`get_object_or_404`).
5. **`alt` descriptif sur toutes les images** (`alt="Garage Steve pro à Douala"`),
   pas de `alt=""` sur les photos de garages/pièces — au contraire sur les
   éléments purement décoratifs.
6. **Maillage interne** : chaque page ville → garages de la ville → pièces
   disponibles ; chaque fiche garage → sa ville + ses services.
7. **Ancres descriptives** : « voir les garages à Douala » plutôt que « cliquez ici ».
8. **Pas de mots-clés bourrés** : le texte doit rester naturel, sinon risque de
   pénalité (voir §12 Conformité).

### 3.2 Balises déjà en place (exemples réels)

| Page | `<title>` | `<meta description>` |
|---|---|---|
| `/` | AutoLink \| Garages et pièces auto vérifiés au Cameroun | Trouvez un garage auto vérifié ou une pièce détachée près de chez vous au Cameroun : Douala, Yaoundé, Buea, Kribi… |
| `/garages/` | Garages auto vérifiés au Cameroun \| AutoLink | Parcourez les garages automobiles vérifiés… filtrez par ville, quartier et service |
| `/garages/ville/douala/` | Garages auto à Douala \| AutoLink | Trouvez un garage automobile vérifié à Douala : mécanique, vidange, diagnostic… |
| `/garages/<slug>/` | `<Garage> — Garage auto à <Ville> \| AutoLink` | `<Garage> à <Ville> : mécanique, vidange… Adresse, horaires, téléphone` |
| `/pieces/` | Pièces détachées auto au Cameroun \| AutoLink | Freinage, moteur, suspension… comparez les prix en FCFA |
| `/pieces/<slug>/` | `<Pièce> — 15 000 FCFA \| AutoLink` | `<Pièce> (Neuf) à 15 000 FCFA chez <Garage>…` |
| `/a-proximite/` | Mécanicien et garage à proximité \| AutoLink | Localisez les garages et mécaniciens vérifiés autour de vous |
| `/compte/connexion/` | Connexion à votre compte AutoLink | *(noindex)* |

### 3.3 Modèle de contenu : page ville (priorité n°1)

URL : `/garages/ville/<ville>/` — déjà implémentée, il reste à **enrichir le
contenu éditorial** (le template actuel liste les garages) :

```text
H1  Garages auto à Douala
H2  Combien de garages vérifiés à Douala ?  (texte 2-3 phrases + compteur réel)
H2  Services les plus demandés à Douala     (vidange, diagnostic, freins…)
H2  Quartiers couverts                      (liens vers pages quartiers)
H2  Questions fréquentes                    (FAQ → balisage FAQPage, § technique)
CTA Contacter un garage vérifié / Inscrire mon garage à Douala
```

### 3.4 Architecture de contenu à créer (ordre de priorité)

1. **Enrichir les pages villes** (Douala, Yaoundé, Buea, Kribi, Limbé…) avec le
   texte §3.3 + FAQ. C'est le levier le plus rentable.
2. **Pages quartiers** (`/garages/ville/douala/bonapriso/`) : `Neighborhood`
   existe déjà en base (`core/models.py`) — même mécanique que les villes.
3. **Finaliser `/categories/<slug>/`** : le template
   `templates/public/pages/catalog/category_detail.html` fait 2 lignes (il étend
   `dashboard/base.html` sans bloc `content`) → page vide. À reconstruire sur
   `public/base.html` (titre/H1/description par catégorie), puis à ré-ajouter
   au sitemap (`CategorySitemap` a été volontairement retiré pour ne pas
   soumettre une page vide).
4. **Page B2B « Inscrire mon garage »** (`/garages/creer/` est privé) : créer
   une page publique marketing expliquant l'activation payante, avec les
   témoignages réels (`core.models.Testimonial`) — c'est la requête n°11.
5. **Guides / blog** (`/guides/<slug>/`) : « Prix moyens des réparations au
   Cameroun », « Que faire quand la voiture ne démarre pas ? », « Choisir son
   mécanicien à Douala ». Chaque guide se termine par un CTA vers les garages
   de la ville concernée.
6. **Pages marque/modèle** : `/pieces/toyota/`, `/pieces/hyundai/` — construites
   depuis `Part.reference_fabricant` quand les données seront assez riches.

> Astuce « link magnet » : publier chaque année une **étude de prix** basée sur
> les données réelles de la plateforme (`GarageService.price_min/price_max`,
> `Part.price`). C'est unique, citable, et c'est ce qui attire des liens
> naturels de la presse locale (§8).

### 3.5 Images et médias

- Les photos de garages/pièces viennent de `media/` : servir en `WebP`/`AVIF`
  si possible, et **toujours** renseigner un `alt` explicite.
- L'image OpenGraph par défaut est générée par `manage.py build_og_image`
  (relancer après un changement de logo). Les fiches garage/pièce utilisent
  automatiquement leur photo principale comme `og:image`.
- Vérifier la compression côté client (Tailwind + `<img loading="lazy">` sur les
  listes sous la ligne de flottaison).

### 3.6 SEO local (le plus fort au Cameroun)

1. **Google Business Profile** (« AutoLink — garages et pièces auto ») en
   catégorie *Service de recherche de garages* / *Marché de pièces auto* :
   adresse vérifiable, horaires, photos réelles, message WhatsApp.
2. **NAP cohérent partout** (nom, adresse, téléphone identiques sur le site, le
   Business Profile, Facebook, annuaires). Le téléphone affiché dans le footer
   doit être cliquable (`tel:`).
3. **Avis clients** : encourager les avis Google après une réparation réussie ;
   ne jamais acheter ni fabriquer d'avis (risque de suspension).
4. **Pages villes + quartiers** = la couche « local landing pages » qui capte
   les requêtes « garage + quartier ».
5. **Balisage `AutoRepair`** (déjà en place sur les fiches) : horaires,
   géocoordonnées, services — c'est ce qui alimente les affichages enrichis.

---

## 4. SEO technique

### 4.1 Ce qui est déjà configuré

- **HTTPS + HSTS** : `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS=31536000`,
  `includeSubDomains`, `preload` (settings.py, hors DEBUG).
- **Domaine canonique unique** : `PUBLIC_SITE_URL` pilote canonical, OG, sitemap
  et robots.txt ; la redirection `www → apex` est dans `deploy/Caddyfile.autolink`.
- **`robots.txt`** : autorise l'exploration, bloque `/admin/`, `/compte/`,
  `/accounts/`, `/paiement*`, `/messages/`, `/tickets/`, `/api/`, `/*/api/`,
  `/sw.js`, `/offline/`, et déclare le sitemap.
  `/recherche/` n'est **pas** bloqué : il doit être explorable pour voir son
  `noindex` (un `Disallow` empêcherait Google de lire la balise).
- **`sitemap.xml`** : généré par `django.contrib.sitemaps` en 4 sections
  (`static`, `villes`, `garages`, `pieces`) — `/sitemap.xml?section=garages`.
  `lastmod` n'est renseigné que là où il est fiable (`Garage.updated_at`,
  `Part.updated_at`), conformément aux recommandations Google.
- **Canonical** : auto-référent sur chaque page ; les listes filtrées sont
  consolidées (`/garages/?city=douala` → `/garages/ville/douala/`) ; `page` est
  conservé pour la pagination.
  *Choix assumé* : sur les facettes (`?service=`, `?sort=`, `?q=`), on n'ajoute
  **pas** de `noindex` — Google recommande le canonical seul pour les facettes,
  les deux signaux combinés étant contradictoires. Le `noindex` est réservé aux
  pages sans équivalent canonique (`/recherche/`, login, espaces privés).
- **`noindex`** (`X-Robots-Tag`) sur toutes les zones privées via
  `autolink/middleware.py` — vérifiable : `curl -sI https://…/compte/connexion/`.
- **Données structurées** : `Organization`, `WebSite` + `SearchAction` (toutes
  pages), `BreadcrumbList`, `AutoRepair` (fiches garage), `Product` + `Offer`
  (fiches pièce, prix en `XAF`).
- **PWA** : `manifest.json` + service worker `sw.js` qui ne met en cache **que**
  la page hors ligne (pas de contenu obsolète servi à Googlebot).

### 4.2 Points d'attention techniques

| Sujet | Action |
|---|---|
| **Framework `sites`** | `SITE_ID = 1` mais le domaine de l'objet `Site` vaut encore `example.com` : le corriger (admin, ou `Site.objects.filter(pk=1).update(domain="autolink.cohub.site", name="AutoLink")`) pour les e-mails allauth et les URL absolues hors sitemap. |
| **`hreflang` / multilingue** | Aucune URL traduite (`locale/` est vide, pas d'`i18n_patterns`) → **ne rien ajouter** tant que l'anglais n'a pas de vraies pages. Un `hreflang` vers des pages identiques est une erreur. |
| **Sitemap index** | Inutile pour l'instant (< 50 000 URLs et < 50 Mo). À prévoir si le catalogue dépasse ce seuil (`django.contrib.sitemaps.views.index`). |
| **Pages catégories** | Vides aujourd'hui → exclues du sitemap et `noindex` (`/categories/` dans le middleware). À réactiver une fois le template reconstruit. |
| **Contenu généré côté client** | Le live ticker et les compteurs de la home sont injectés en JS : ce contenu n'est pas lu de façon fiable par Googlebot → ne jamais y placer d'information SEO critique. |
| **Performance (Core Web Vitals)** | Cible : LCP < 2,5 s, INP < 200 ms, CLS < 0,1. Pistes : compression Caddy (`encode zstd gzip`, déjà en place), cache long sur `/static/` (fait), `loading="lazy"` + `width`/`height` sur les images, limiter les polices ; `output.css` est déjà minifié par Tailwind. |
| **Cache serveur** | `LocMemCache` est propre à chaque worker gunicorn : ne pas baser le contenu SEO ou la pagination sur ce cache. |
| **404 / 301** | Si une URL change (ex. `?category=` → `/categories/…`), ajouter une redirection 301 explicite. Ne jamais supprimer une URL indexée sans redirection. |

---

## 5. SEO off-page (netlinking & autorité)

Objectif réaliste pour un site jeune : **10-15 liens de qualité** dans les 3
premiers mois, plutôt que 200 liens d'annuaires automatiques (risque de spam).

### 5.1 Où obtenir des liens (par ordre de valeur)

1. **Partenariats avec les garages inscrits** (le plus naturel) : demander à
   chaque garage de mettre le lien de sa fiche AutoLink sur sa page Facebook /
   sa fiche Google / son site. Fournir un kit prêt à l'emploi (URL + visuel +
   texte). 20 garages = 20 liens contextuels locaux.
2. **Presse et blogs locaux** : médias tech/éco camerounais, journaux auto,
   podcasts mobilité. Angle : « première plateforme qui vérifie les garages »,
   étude de prix (§3.4), couverture par ville.
3. **Annuaires d'entreprises** : Google Business Profile (priorité 1), Pages
   Jaunes du Cameroun, GoAfricaOnline, Kompass Cameroun — toujours avec un NAP
   identique. Vérifier chaque annuaire avant inscription (pas d'annuaire « SEO »
   de masse sans trafic réel).
4. **Guest blogging** : blogs auto/tech africains, écoles de mécanique,
   associations de transporteurs et syndicats de taxis/bus (contenu utile à
   leurs membres + lien).
5. **Communautés (trafic + marque, liens souvent en `nofollow`)** : Facebook
   (groupes vente/recherche de pièces Douala/Yaoundé), LinkedIn (garages,
   gestionnaires de flottes), WhatsApp Business, TikTok/YouTube (démos d'atelier).
6. **Données citables** : l'étude de prix annuelle (§3.4) — le seul moyen
   d'obtenir des liens éditoriaux sans prospection agressive.

### 5.2 Modèle d'outreach (e-mail)

```text
Objet : Une donnée inédite sur les prix des réparations auto au Cameroun

Bonjour <Prénom>,

Je suis <Nom>, <Rôle> chez AutoLink (autolink.cohub.site), la plateforme qui
référence les garages vérifiés et les pièces détachées au Cameroun.

Nous avons compilé les prix pratiqués par <N> garages à Douala et Yaoundé :
vidange (<prix> FCFA), diagnostic (<prix> FCFA), plaquettes (<prix> FCFA).
L'étude complète est ici : <URL de la page étude>.

Si cela peut servir à vos lecteurs, vous êtes libre de citer les chiffres — je
peux aussi vous envoyer le graphique en haute résolution ou répondre à vos
questions pour un article.

Bien cordialement,
<Nom> — <site> — <téléphone>
```

### 5.3 Modèle de message WhatsApp (partenariat garage)

```text
Bonjour <Prénom>, c'est <Nom> d'AutoLink.
Votre garage <Nom du garage> est vérifié et visible ici : <URL de la fiche>.
Pour renforcer votre visibilité locale, vous pouvez :
1) ajouter ce lien sur votre page Facebook et votre fiche Google,
2) répondre rapidement aux demandes reçues depuis la plateforme,
3) demander à vos clients satisfaits de laisser un avis Google.
Je vous envoie le visuel + le texte prêt à publier si vous voulez.
```

### 5.4 À proscrire (black hat)

Achat de liens en masse, réseaux de blogs privés (PBN), échanges de liens
automatisés, annuaires spam, commentaires avec ancre optimisée, contenu dupliqué,
avis fabriqués, pages « doorway » par ville sans contenu réel. Ces pratiques
exposent à une action manuelle Google.

---

## 6. Google Search Console : procédure pas à pas

### 6.1 Créer et vérifier la propriété

1. Aller sur <https://search.google.com/search-console> → **Ajouter une propriété**.
2. Choisir **Domaine** (recommandé) → saisir `autolink.cohub.site` :
   - Google demande un enregistrement **DNS TXT** :
     `TXT  @  "google-site-verification=…"` (à ajouter chez le gestionnaire DNS
     de `cohub.site`) → puis **Vérifier**.
   - Cette méthode couvre `autolink.cohub.site` **et** `www.autolink.cohub.site`.
3. *Alternative* (propriété « Préfixe d'URL ») : copier la **balise HTML**
   fournie, la mettre dans `GOOGLE_SITE_VERIFICATION` du `.env`, redémarrer
   l'application, puis contrôler :
   `curl -s https://autolink.cohub.site/ | grep google-site-verification`.

### 6.2 Soumettre le sitemap

1. Vérifier côté serveur : `curl -sI https://autolink.cohub.site/sitemap.xml`
   → doit répondre `200` avec `Content-Type: application/xml`.
2. Dans GSC → **Sitemaps** → saisir `sitemap.xml` → **Envoyer**.
3. Les sections sont accessibles séparément si besoin :
   `/sitemap.xml?section=garages`, `…?section=villes`, `…?section=pieces`, `…?section=static`.

### 6.3 Demander l'indexation initiale

Utiliser **Inspecter une URL** → « Demander une indexation » pour ces pages
(10-15 demandes maximum au début) :

- `https://autolink.cohub.site/`
- `https://autolink.cohub.site/garages/`
- `https://autolink.cohub.site/garages/ville/douala/` (une ville avec de vrais garages)
- une fiche garage réelle
- `https://autolink.cohub.site/pieces/`
- `https://autolink.cohub.site/a-proximite/`
- `https://autolink.cohub.site/contact/`

### 6.4 Suivi hebdomadaire (10 minutes)

| Rapport GSC | Ce qu'on regarde | Action si problème |
|---|---|---|
| **Pages** (indexation) | Pages valides / « Explorée, non indexée » / « Exclue par noindex » | Les noindex doivent se limiter aux zones privées |
| **Erreurs d'exploration** | 404, 5xx, redirections | 404 sur une ancienne URL indexée → créer une 301 ; 5xx → corriger (logs) |
| **Performances** | Impressions, clics, CTR, position + requêtes réelles | Intégrer la requête qui progresse dans le contenu (titre, H2, FAQ) |
| **Sitemaps** | Dernière lecture, URLs découvertes | Re-soumettre si « Impossible de récupérer » |
| **Données structurées** | Erreurs AutoRepair / Product / BreadcrumbList | Corriger dans `core/templatetags/seo_tags.py` |
| **Core Web Vitals** | URLs « À améliorer » | Compresser les images, revoir les polices |

## 7. Google Analytics 4 (ou alternative)

### 7.1 Installation (déjà prévue dans le code)

1. Créer une propriété GA4 → récupérer l'identifiant `G-XXXXXXXXXX`.
2. Le renseigner dans `.env` : `GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX` → redémarrer.
3. Le snippet n'est injecté **que** si l'ID est présent (`templates/public/base.html`) :
   rien ne fuit en développement.
4. Dans GA4 → **Admin → Correspondances de produits** : lier Search Console.
5. Vérifier via GA4 → **Rapports → Temps réel** en visitant le site.

### 7.2 Événements à mesurer (prioritaires)

Le snippet envoie aujourd'hui uniquement `page_view`. À brancher dans
`static/js/app.js` lorsque le besoin est confirmé :

| Événement | Déclencheur | Pourquoi |
|---|---|---|
| `contact_garage_click` | Clic `tel:` / WhatsApp sur une fiche garage | Conversion principale côté client |
| `part_contact_click` | Clic contact sur une fiche pièce | Intention d'achat |
| `garage_signup_start` | Ouverture du formulaire d'inscription garage | Haut de tunnel B2B |
| `garage_payment_success` | Retour de paiement CamPay réussi | Conversion payante (revenu) |
| `search_performed` | Soumission de `/recherche/` ou filtres `/garages/` | Besoins réels des utilisateurs |
| `pwa_install` | Événement `appinstalled` (déjà capté dans `base.html`) | Trafic récurrent |

> Alternative respectueuse de la vie privée : **Matomo** auto-hébergé sur le
> même VPS, ou Umami.

### 7.3 Outils d'audit

| Outil | Usage | Fréquence |
|---|---|---|
| Search Console | Indexation, requêtes, erreurs, Core Web Vitals | Hebdomadaire |
| PageSpeed Insights | LCP / INP / CLS mobile (priorité 3G/4G Cameroun) | Mensuel |
| Test des résultats enrichis | Valider AutoRepair / Product / Breadcrumb | À chaque modification de `seo_tags.py` |
| Validator.schema.org | Vérifier le JSON-LD ligne par ligne | Ponctuel |
| Screaming Frog (gratuit < 500 URLs) | Titres dupliqués, 404, canonicals | Mensuel |
| Lighthouse (Chrome DevTools) | Performance / accessibilité / SEO | Mensuel |

---

## 8. Plan d'action 30 / 60 / 90 jours

### Jours 1-30 — Fondations et indexation

- [ ] Corriger le domaine de l'objet `Site` Django (`example.com` → `autolink.cohub.site`).
- [ ] Déployer ce lot SEO : `robots.txt`, `sitemap.xml`, canonical, OG, JSON-LD, image OG.
- [ ] Vérifier HTTPS + redirection `www → apex` dans Caddy.
- [ ] Créer la propriété Search Console (méthode DNS) et soumettre le sitemap.
- [ ] Créer/réclamer le **Google Business Profile** avec un NAP cohérent.
- [ ] Créer la propriété GA4 et renseigner `GOOGLE_ANALYTICS_ID`.
- [ ] Enrichir 2 pages villes (Douala, Yaoundé) : contenu + FAQ (§3.3).
- [ ] Vérifier les attributs `alt` des images et corriger les manquants.

### Jours 31-60 — Contenu et volume

- [ ] Créer les pages quartiers des villes actives (Bonapriso, Bonabéri, …).
- [ ] Reconstruire `/categories/<slug>/` sur `public/base.html`, puis le remettre au sitemap.
- [ ] Publier la page publique « Inscrire mon garage » (requête B2B n°11).
- [ ] Publier 3 guides (prix des réparations, panne de démarrage, choisir un mécanicien).
- [ ] Nettoyer les données : descriptions de garages > 200 caractères, services renseignés, photos réelles.
- [ ] Contacter les 10 premiers garages pour les liens Facebook/Google + avis clients.
- [ ] Audit Screaming Frog (titres dupliqués, 404, canonicals) et corrections.

### Jours 61-90 — Autorité et itération

- [ ] Publier l'étude de prix annuelle (link magnet) + outreach presse/blog (§5.2).
- [ ] 2 guest posts (blog auto local + école de mécanique / association de transporteurs).
- [ ] 3 à 5 inscriptions d'annuaires vérifiés (NAP identique).
- [ ] Brancher les événements GA4 de conversion (§7.2) et créer le tableau de bord mensuel.
- [ ] Réécrire les titres/descriptions des pages à fort affichage mais CTR < 2 %.
- [ ] Mettre à jour les FAQ des pages villes avec les requêtes réelles de GSC.

## 9. Indicateurs et suivi mensuel

| Indicateur | Source | Objectif 3 mois | Objectif 6 mois |
|---|---|---|---|
| Pages indexées | GSC → Pages | 20-30 | 100+ |
| Impressions organiques / mois | GSC → Performances | 1 000 | 10 000 |
| Clics organiques / mois | GSC → Performances | 100 | 1 000 |
| Position moyenne | GSC → Performances | < 30 | < 15 |
| Requêtes en top 10 | GSC | 5 | 30 |
| Clics contact garage (tél/WhatsApp) | GA4 | 30 / mois | 200 / mois |
| Inscriptions garages via SEO | GA4 + base | 3 | 15 |
| Core Web Vitals (mobile) | GSC | Toutes « Bonnes » | Maintenu |
| Liens entrants de qualité | GSC → Liens / Ahrefs | 10 | 30 |

**Routine mensuelle** (1 h) : exporter GSC (requêtes + pages) → repérer les
pages à CTR faible → réécrire titres/descriptions → vérifier les nouvelles
requêtes pour créer le contenu du mois → contrôler les 404/5xx → mettre à jour
le tableau ci-dessus.

## 10. Checklist avant indexation (à passer avant la demande GSC)

### Technique

- [ ] `curl -sI https://autolink.cohub.site/ | head -1` → `HTTP/2 200`
- [ ] `curl -sI https://autolink.cohub.site/` → présence de `strict-transport-security`
- [ ] `curl -s https://autolink.cohub.site/robots.txt` → doit contenir `Sitemap: https://autolink.cohub.site/sitemap.xml`
- [ ] `curl -sI https://autolink.cohub.site/sitemap.xml` → `200` + `application/xml`
- [ ] `curl -s https://autolink.cohub.site/sitemap.xml | grep -c "<loc>"` > 0
- [ ] Redirection `www` : `curl -sI https://www.autolink.cohub.site/ | grep -i location` → `https://autolink.cohub.site/…` (301)
- [ ] Aucun `noindex` sur les pages publiques :
      `curl -sI https://autolink.cohub.site/garages/ | grep -i x-robots-tag` → **vide**
- [ ] `noindex` bien présent sur les zones privées :
      `curl -sI https://autolink.cohub.site/compte/connexion/ | grep -i x-robots-tag`
- [ ] Canonical juste : `curl -s https://autolink.cohub.site/garages/ | grep canonical`
- [ ] `PUBLIC_SITE_URL` correct dans `.env` (aucune URL ngrok/localhost dans le HTML public)
- [ ] Domaine de l'objet `Site` corrigé (framework `sites`)
- [ ] Certificat SSL valide (aucun avertissement navigateur ; renouvellement Caddy automatique actif)

### Contenu et balises

- [ ] Toutes les pages publiques ont un `<title>` **unique** (audit Screaming Frog)
- [ ] Toutes les pages publiques ont une `meta description` **unique**
- [ ] Un seul `<h1>` par page, contenant le mot-clé principal
- [ ] Images avec `alt` descriptif (photos de garages/pièces)
- [ ] Aucun texte lorem ipsum / texte de test (ex. vérifier `templates/offline.html` qui contient encore `Hors ligne ttt` et les descriptions de garages de test)
- [ ] Contenu suffisant sur les pages villes/quartiers (pas de page vide)
- [ ] Maillage interne : chaque page ville/garage/pièce atteignable en ≤ 3 clics depuis l'accueil

### Performance et mobile

- [ ] PageSpeed Insights (mobile) : LCP < 2,5 s sur `/` et une fiche garage
- [ ] Test d'ergonomie mobile Google : aucune erreur
- [ ] Aucune erreur bloquante dans les données structurées :
      <https://search.google.com/test/rich-results>
- [ ] JSON-LD valide : <https://validator.schema.org/>

### Indexation

- [ ] Sitemap soumis dans Search Console
- [ ] Demande d'indexation envoyée pour les 7 pages prioritaires (§6.3)
- [ ] GA4 en temps réel opérationnel
- [ ] Aucune action manuelle / sécurité signalée dans GSC → **Sécurité et actions manuelles**

---

## 11. Conformité et bonnes pratiques

- **Spam policies Google** : pas de texte caché, pas de redirection trompeuse,
  pas de pages satellites, pas de contenu généré automatiquement sans valeur
  ajoutée, pas de spam de mots-clés.
- **Avis et témoignages** : `core.models.Testimonial` doit contenir **uniquement
  de vrais retours** (le modèle le précise déjà dans son docstring) et le
  balisage `AggregateRating` n'est **pas** utilisé tant qu'il n'y a pas de vrais
  avis vérifiables associés à chaque garage — c'est volontaire.
- **Expérience utilisateur d'abord** : vitesse, mobile, contenu utile. Un
  positionnement obtenu par le bourrage de mots-clés se retourne toujours contre
  le site à moyen terme.
- **Données personnelles** : si Google Analytics est activé, ajouter une mention
  dans la page « Politique et règles » (`/politique-et-regles/`) et prévoir la
  possibilité de refus (ou choisir Matomo auto-hébergé).

## 12. Annexe A — Commandes de vérification

```bash
# 1. robots.txt et sitemap
curl -s https://autolink.cohub.site/robots.txt
curl -sI https://autolink.cohub.site/sitemap.xml
curl -s https://autolink.cohub.site/sitemap.xml | grep -c "<loc>"

# 2. Balises d'une page (titre, canonical, OG, JSON-LD)
curl -s https://autolink.cohub.site/ | grep -E '<title>|canonical|og:title'
curl -s https://autolink.cohub.site/garages/ | grep -c 'application/ld+json'

# 3. noindex : rien sur le public, présent sur le privé
curl -sI https://autolink.cohub.site/garages/ | grep -i x-robots-tag      # vide attendu
curl -sI https://autolink.cohub.site/compte/connexion/ | grep -i x-robots-tag
curl -sI https://autolink.cohub.site/administration/dashboard/ | grep -i x-robots-tag

# 4. Redirections
curl -sI https://www.autolink.cohub.site/ | grep -iE 'HTTP/|location'
curl -sI http://autolink.cohub.site/ | grep -iE 'HTTP/|location'

# 5. Côté serveur (dans le conteneur)
python manage.py check
python manage.py build_og_image        # régénère static/og-image.jpg
python manage.py collectstatic --noinput
```

## 13. Annexe B — Variables d'environnement SEO

| Variable | Rôle | Exemple |
|---|---|---|
| `PUBLIC_SITE_URL` | Domaine canonique (canonical, OG, sitemap, robots) | `https://autolink.cohub.site` |
| `GOOGLE_SITE_VERIFICATION` | Balise de vérification Search Console | `abc123…` |
| `GOOGLE_ANALYTICS_ID` | Identifiant GA4 (vide = pas de GA) | `G-XXXXXXXXXX` |

> `SITE_URL` reste dédié aux webhooks de paiement (peut contenir plusieurs
> domaines séparés par des virgules) : **ne pas l'utiliser pour le SEO**.

## 14. Annexe C — Fichiers SEO du projet

| Fichier | Rôle |
|---|---|
| `core/seo.py` | URL canonique, URL absolue, troncature, JSON-LD |
| `core/sitemaps.py` | Sitemaps statique / villes / garages / pièces |
| `core/views/seo.py` | Vue `robots.txt` |
| `core/templatetags/seo_tags.py` | `seo_organization_json_ld`, `garage_json_ld`, `part_json_ld`, `breadcrumb_json_ld` |
| `autolink/context_processors.py` | Variables SEO injectées dans tous les templates |
| `autolink/urls.py` | Routes `/robots.txt` et `/sitemap.xml` |
| `autolink/middleware.py` | `X-Robots-Tag: noindex` sur les zones privées |
| `templates/public/base.html` | `<head>` SEO (title, description, robots, canonical, OG, Twitter, JSON-LD, GA4) |
| `core/management/commands/build_og_image.py` | Génération de `static/og-image.jpg` |
| `deploy/Caddyfile.autolink` | Redirection www, cache, compression, journaux |

## 15. Prochaines actions immédiates (ordre conseillé)

1. Mettre à jour `.env` en production (`PUBLIC_SITE_URL`, puis GA4/GSC) et
   **redéployer** (les templates sont mis en cache au démarrage).
2. Corriger le domaine de l'objet `Site` Django.
3. Créer et vérifier la propriété Search Console, soumettre `sitemap.xml`.
4. Enrichir les pages villes **Douala** et **Yaoundé** (contenu + FAQ).
5. Nettoyer les données de test (villes `hhh`/`hhggggg`, descriptions, photos)
   avant d'inviter Google à explorer le site.
6. Reconstruire la page `/categories/<slug>/` puis la réactiver dans le sitemap.
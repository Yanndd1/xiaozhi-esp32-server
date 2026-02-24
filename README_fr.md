[![Banners](docs/images/banner1.png)](https://github.com/xinnan-tech/xiaozhi-esp32-server)

<h1 align="center">Service Backend Xiaozhi — xiaozhi-esp32-server</h1>

<p align="center">
Ce projet est un systeme logiciel et materiel intelligent base sur la theorie de l'intelligence symbiotique homme-machine<br/>fournissant les services backend pour le projet open-source de materiel intelligent
<a href="https://github.com/78/xiaozhi-esp32">xiaozhi-esp32</a><br/>
Developpe en Python, Java et Vue selon le <a href="https://ccnphfhqs21z.feishu.cn/wiki/M0XiwldO9iJwHikpXD5cEx71nKh">Protocole de Communication Xiaozhi</a><br/>
Prise en charge des protocoles MQTT+UDP, WebSocket, point d'acces MCP, reconnaissance vocale et base de connaissances
</p>

<p align="center">
<a href="./docs/FAQ.md">FAQ</a>
· <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/issues">Signaler un probleme</a>
· <a href="./README.md#%E9%83%A8%E7%BD%B2%E6%96%87%E6%A1%A3">Documentation de deploiement</a>
· <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/releases">Notes de version</a>
</p>

<p align="center">
  <a href="./README.md"><img alt="简体中文版自述文件" src="https://img.shields.io/badge/简体中文-DFE0E5"></a>
  <a href="./README_en.md"><img alt="README in English" src="https://img.shields.io/badge/English-DFE0E5"></a>
  <a href="./README_fr.md"><img alt="Francais" src="https://img.shields.io/badge/Français-DBEDFA"></a>
  <a href="./README_vi.md"><img alt="Tiếng Việt" src="https://img.shields.io/badge/Tiếng Việt-DFE0E5"></a>
  <a href="./README_de.md"><img alt="Deutsch" src="https://img.shields.io/badge/Deutsch-DFE0E5"></a>
  <a href="./README_pt_BR.md"><img alt="Português (Brasil)" src="https://img.shields.io/badge/Português (Brasil)-DFE0E5"></a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/releases">
    <img alt="GitHub Contributors" src="https://img.shields.io/github/v/release/xinnan-tech/xiaozhi-esp32-server?logo=docker" />
  </a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/LICENSE">
    <img alt="GitHub pull requests" src="https://img.shields.io/badge/license-MIT-white?labelColor=black" />
  </a>
  <a href="https://github.com/xinnan-tech/xiaozhi-esp32-server">
    <img alt="stars" src="https://img.shields.io/github/stars/xinnan-tech/xiaozhi-esp32-server?color=ffcb47&labelColor=black" />
  </a>
</p>

<p align="center">
Dirige par l'equipe du Professeur Siyuan Liu (Universite de Technologie de Chine du Sud)
</br>
<img src="./docs/images/hnlg.jpg" alt="Universite de Technologie de Chine du Sud" width="50%">
</p>

---

## Utilisateurs cibles

Ce projet necessite du materiel ESP32 pour fonctionner. Si vous avez achete du materiel ESP32, que vous l'avez connecte avec succes au service backend deploye, et que vous souhaitez construire votre propre service backend `xiaozhi-esp32` de maniere independante, alors ce projet est fait pour vous.

Vous voulez voir le resultat ? Cliquez sur les videos ci-dessous

<table>
  <tr>
    <td>
        <a href="https://www.bilibili.com/video/BV1FMFyejExX" target="_blank">
         <picture>
           <img alt="Vitesse de reponse" src="docs/images/demo9.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1vchQzaEse" target="_blank">
         <picture>
           <img alt="Astuces d'optimisation" src="docs/images/demo6.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1C1tCzUEZh" target="_blank">
         <picture>
           <img alt="Scenario medical complexe" src="docs/images/demo1.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1zUW5zJEkq" target="_blank">
         <picture>
           <img alt="Envoi de commandes MQTT" src="docs/images/demo4.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1Exu3zqEDe" target="_blank">
         <picture>
           <img alt="Reconnaissance vocale" src="docs/images/demo14.png" />
         </picture>
        </a>
    </td>
  </tr>
  <tr>
    <td>
        <a href="https://www.bilibili.com/video/BV1pNXWYGEx1" target="_blank">
         <picture>
           <img alt="Controle domotique" src="docs/images/demo5.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1ZQKUzYExM" target="_blank">
         <picture>
           <img alt="Point d'acces MCP" src="docs/images/demo13.png" />
         </picture>
        </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1TJ7WzzEo6" target="_blank">
         <picture>
           <img alt="Taches multi-instructions" src="docs/images/demo11.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1VC96Y5EMH" target="_blank">
         <picture>
           <img alt="Lecture de musique" src="docs/images/demo7.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1Z8XuYZEAS" target="_blank">
         <picture>
           <img alt="Plugin meteo" src="docs/images/demo8.png" />
         </picture>
        </a>
    </td>
  </tr>
  <tr>
    <td>
      <a href="https://www.bilibili.com/video/BV12J7WzBEaH" target="_blank">
         <picture>
           <img alt="Interruption en temps reel" src="docs/images/demo10.png" />
         </picture>
        </a>
    </td>
    <td>
      <a href="https://www.bilibili.com/video/BV1Co76z7EvK" target="_blank">
         <picture>
           <img alt="Reconnaissance d'objets par photo" src="docs/images/demo12.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV1CDKWemEU6" target="_blank">
         <picture>
           <img alt="Personnalisation de la voix" src="docs/images/demo2.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV12yA2egEaC" target="_blank">
         <picture>
           <img alt="Communication en cantonais" src="docs/images/demo3.png" />
         </picture>
        </a>
    </td>
    <td>
        <a href="https://www.bilibili.com/video/BV17LXWYvENb" target="_blank">
         <picture>
           <img alt="Lecture des actualites" src="docs/images/demo0.png" />
         </picture>
        </a>
    </td>
  </tr>
</table>

---

## Avertissements

1. Ce projet est un logiciel open-source. Ce logiciel n'a aucun partenariat commercial avec les fournisseurs de services API tiers (y compris, mais sans s'y limiter, la reconnaissance vocale, les grands modeles, la synthese vocale et autres plateformes) auxquels il s'interface, et ne fournit aucune forme de garantie concernant la qualite de leur service ou la securite financiere. Il est recommande aux utilisateurs de privilegier les fournisseurs de services disposant des licences commerciales appropriees et de lire attentivement leurs conditions d'utilisation et politiques de confidentialite. Ce logiciel n'heberge aucune cle de compte, ne participe a aucun flux de fonds et ne supporte pas le risque de perte de fonds recharges.

2. Les fonctionnalites de ce projet ne sont pas completes et n'ont pas passe d'audit de securite reseau. Veuillez ne pas l'utiliser en environnement de production. Si vous deployez ce projet a des fins d'apprentissage dans un environnement reseau public, veuillez vous assurer que les mesures de protection necessaires sont en place.

---

## Documentation de deploiement

![Banners](docs/images/banner2.png)

Ce projet propose deux methodes de deploiement. Veuillez choisir en fonction de vos besoins :

#### Choix de la methode de deploiement
| Methode de deploiement | Caracteristiques | Scenarios d'utilisation | Documentation | Configuration requise | Tutoriels video |
|---------|------|---------|---------|---------|---------|
| **Installation simplifiee** | Dialogue intelligent, gestion d'un seul agent | Environnements a faible configuration, donnees stockees dans des fichiers de config, pas de base de donnees requise | [Version Docker](./docs/Deployment.md#%E6%96%B9%E5%BC%8F%E4%B8%80docker%E5%8F%AA%E8%BF%90%E8%A1%8Cserver) / [Deploiement depuis les sources](./docs/Deployment.md#%E6%96%B9%E5%BC%8F%E4%BA%8C%E6%9C%AC%E5%9C%B0%E6%BA%90%E7%A0%81%E5%8F%AA%E8%BF%90%E8%A1%8Cserver)| 2 coeurs 4 Go avec `FunASR`, 2 coeurs 2 Go si tout en API | - |
| **Installation complete** | Dialogue intelligent, gestion multi-utilisateurs, gestion multi-agents, interface console intelligente | Experience complete, donnees stockees en base de donnees | [Version Docker](./docs/Deployment_all.md#%E6%96%B9%E5%BC%8F%E4%B8%80docker%E8%BF%90%E8%A1%8C%E5%85%A8%E6%A8%A1%E5%9D%97) / [Deploiement depuis les sources](./docs/Deployment_all.md#%E6%96%B9%E5%BC%8F%E4%BA%8C%E6%9C%AC%E5%9C%B0%E6%BA%90%E7%A0%81%E8%BF%90%E8%A1%8C%E5%85%A8%E6%A8%A1%E5%9D%97) / [Mise a jour automatique](./docs/dev-ops-integration.md) | 4 coeurs 8 Go avec `FunASR`, 2 coeurs 4 Go si tout en API | [Tutoriel video](https://www.bilibili.com/video/BV1wBJhz4Ewe) |

Pour les questions frequentes et tutoriels associes, consultez [ce lien](./docs/FAQ.md)

> Note : Ci-dessous se trouve une plateforme de test deployee avec le dernier code. Vous pouvez flasher et tester si necessaire. Utilisateurs simultanes : 6, les donnees sont effacees quotidiennement.

```
Adresse de la console intelligente : https://2662r3426b.vicp.fun
Adresse de la console intelligente (H5) : https://2662r3426b.vicp.fun/h5/index.html

Outil de test du service : https://2662r3426b.vicp.fun/test/
Adresse de l'interface OTA : https://2662r3426b.vicp.fun/xiaozhi/ota/
Adresse de l'interface WebSocket : wss://2662r3426b.vicp.fun/xiaozhi/v1/
```

#### Description et recommandations de configuration
> [!Note]
> Ce projet propose deux schemas de configuration :
>
> 1. `Configuration gratuite de base` : Adaptee a un usage personnel et domestique, tous les composants utilisent des solutions gratuites, aucun paiement supplementaire requis.
>
> 2. `Configuration streaming` : Adaptee aux demonstrations, formations, scenarios avec plus de 2 utilisateurs simultanes, etc. Utilise la technologie de traitement en streaming pour une vitesse de reponse plus rapide et une meilleure experience.
>
> Depuis la version `0.5.2`, le projet prend en charge la configuration streaming. Par rapport aux versions anterieures, la vitesse de reponse est amelioree d'environ `2,5 secondes`, ameliorant significativement l'experience utilisateur.

| Nom du module | Configuration gratuite de base | Configuration streaming |
|:---:|:---:|:---:|
| ASR (Reconnaissance vocale) | FunASR (local) | XunfeiStreamASR (streaming iFLYTEK) |
| LLM (Grand modele) | glm-4-flash (Zhipu) | qwen-flash (Alibaba Bailian) |
| VLLM (Modele de vision) | glm-4v-flash (Zhipu) | qwen2.5-vl-3b-instruct (Alibaba Bailian) |
| TTS (Synthese vocale) | LinkeraiTTS (streaming Lingxi) | HuoshanDoubleStreamTTS (streaming Volcano) |
| Intent (Reconnaissance d'intention) | function_call (appel de fonction) | function_call (appel de fonction) |
| Memory (Memoire) | mem_local_short (memoire locale court terme) | mem_local_short (memoire locale court terme) |

Si vous etes preoccupe par la latence de chaque composant, consultez le [Rapport de performance des composants Xiaozhi](https://github.com/xinnan-tech/xiaozhi-performance-research), et testez dans votre propre environnement en suivant les methodes du rapport.

#### Outils de test
Ce projet fournit les outils de test suivants pour vous aider a verifier le systeme et choisir les modeles adaptes :

| Nom de l'outil | Emplacement | Methode d'utilisation | Description |
|:---:|:---|:---:|:---:|
| Outil de test d'interaction audio | main > xiaozhi-server > test > test_page.html | Ouvrir directement avec Google Chrome | Teste les fonctions de lecture et reception audio, verifie si le traitement audio cote Python fonctionne correctement |
| Outil de test de reponse des modeles | main > xiaozhi-server > performance_tester.py | Executer `python performance_tester.py` | Teste la vitesse de reponse des trois modules principaux : ASR, LLM, VLLM, TTS |

> Note : Lors du test de vitesse des modeles, seuls les modeles dont les cles sont configurees seront testes.

---

## Liste des fonctionnalites

### Implementees
![Architecture - Installation complete](docs/images/deploy2.png)

| Module | Description |
|:---:|:---|
| Architecture centrale | Basee sur la [passerelle MQTT+UDP](https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/mqtt-gateway-integration.md), serveurs WebSocket et HTTP, fournit une console de gestion complete et un systeme d'authentification |
| Interaction vocale | Prise en charge de l'ASR streaming, du TTS streaming, du VAD, reconnaissance multi-langues et traitement vocal |
| Reconnaissance d'empreinte vocale | Inscription, gestion et reconnaissance multi-utilisateurs, traitement en parallele avec l'ASR, identification en temps reel du locuteur transmise au LLM pour des reponses personnalisees |
| Dialogue intelligent | Prise en charge de multiples LLM, dialogue intelligent |
| Perception visuelle | Prise en charge de multiples VLLM, interaction multimodale |
| Reconnaissance d'intention | Reconnaissance d'intention par LLM, appel de fonctions (Function Call), mecanisme de traitement d'intention par plugins |
| Systeme de memoire | Memoire locale court terme, memoire via interface mem0ai, memoire intelligente PowerMem, avec fonctionnalite de synthese de memoire |
| Base de connaissances | Prise en charge de RAGFlow, permettant au LLM de juger si la base de connaissances doit etre consultee apres reception de la question de l'utilisateur |
| Appel d'outils | Protocole IoT client, protocole MCP client, protocole MCP serveur, protocole MCP endpoint, fonctions d'outils personnalisees |
| Envoi de commandes | Envoi de commandes MCP aux appareils ESP32 via protocole MQTT depuis la console intelligente |
| Backend de gestion | Interface Web de gestion, gestion des utilisateurs, configuration systeme et gestion des appareils ; prise en charge du chinois simplifie, chinois traditionnel et anglais |
| Outils de test | Outils de test de performance, de modeles de vision et d'interaction audio |
| Support de deploiement | Deploiement Docker et deploiement local, gestion complete des fichiers de configuration |
| Systeme de plugins | Extensions fonctionnelles par plugins, developpement de plugins personnalises et chargement a chaud |

### En cours de developpement

Pour connaitre l'avancement du plan de developpement, [cliquez ici](https://github.com/users/xinnan-tech/projects/3). Pour les questions frequentes et tutoriels, consultez [ce lien](./docs/FAQ.md)

Si vous etes developpeur, voici une [Lettre ouverte aux developpeurs](docs/contributor_open_letter.md). Bienvenue !

---

## Ecosysteme du produit
Xiaozhi est un ecosysteme. Lorsque vous utilisez ce produit, vous pouvez egalement decouvrir d'autres [excellents projets](https://github.com/78/xiaozhi-esp32/blob/main/README_zh.md#%E7%9B%B8%E5%85%B3%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE) de cet ecosysteme.

---

## Liste des plateformes/composants pris en charge

### LLM - Modeles de langage

| Methode d'utilisation | Plateformes prises en charge | Plateformes gratuites |
|:---:|:---:|:---:|
| Appels via interface OpenAI | Alibaba Bailian, Volcano Engine, DeepSeek, Zhipu, Gemini, iFLYTEK | Zhipu, Gemini |
| Appels via interface Ollama | Ollama | - |
| Appels via interface Dify | Dify | - |
| Appels via interface FastGPT | FastGPT | - |
| Appels via interface Coze | Coze | - |
| Appels via interface Xinference | Xinference | - |
| Appels via interface HomeAssistant | HomeAssistant | - |

En pratique, tout LLM prenant en charge les appels via interface OpenAI peut etre integre et utilise.

---

### VLLM - Modeles de vision

| Methode d'utilisation | Plateformes prises en charge | Plateformes gratuites |
|:---:|:---:|:---:|
| Appels via interface OpenAI | Alibaba Bailian, Zhipu ChatGLMVLLM | Zhipu ChatGLMVLLM |

En pratique, tout VLLM prenant en charge les appels via interface OpenAI peut etre integre et utilise.

---

### TTS - Synthese vocale

| Methode d'utilisation | Plateformes prises en charge | Plateformes gratuites |
|:---:|:---:|:---:|
| Appels via interface | EdgeTTS, iFLYTEK, Volcano Engine, Tencent Cloud, Alibaba Cloud et Bailian, CosyVoiceSiliconflow, TTS302AI, CozeCnTTS, GizwitsTTS, ACGNTTS, OpenAITTS, LinkeraiTTS streaming, MinimaxTTS | LinkeraiTTS streaming, EdgeTTS, CosyVoiceSiliconflow (partiel) |
| Services locaux | FishSpeech, GPT_SOVITS_V2, GPT_SOVITS_V3, Index-TTS, PaddleSpeech | Index-TTS, PaddleSpeech, FishSpeech, GPT_SOVITS_V2, GPT_SOVITS_V3 |

---

### VAD - Detection d'activite vocale

| Type | Nom de la plateforme | Methode d'utilisation | Tarification | Notes |
|:---:|:---------:|:----:|:----:|:--:|
| VAD | SileroVAD | Utilisation locale | Gratuit | |

---

### ASR - Reconnaissance vocale

| Methode d'utilisation | Plateformes prises en charge | Plateformes gratuites |
|:---:|:---:|:---:|
| Utilisation locale | FunASR, SherpaASR | FunASR, SherpaASR |
| Appels via interface | FunASRServer, Volcano Engine, iFLYTEK, Tencent Cloud, Alibaba Cloud, Baidu Cloud, OpenAI ASR | FunASRServer |

---

### Reconnaissance d'empreinte vocale

| Methode d'utilisation | Plateformes prises en charge | Plateformes gratuites |
|:---:|:---:|:---:|
| Utilisation locale | 3D-Speaker | 3D-Speaker |

---

### Stockage memoire

| Type | Nom de la plateforme | Methode d'utilisation | Tarification | Notes |
|:------:|:---------------:|:----:|:---------:|:--:|
| Memoire | mem0ai | Appels via interface | 1000 appels/mois | |
| Memoire | [powermem](./docs/powermem-integration.md) | Synthese locale | Depend du LLM et de la BDD | Open-source OceanBase, recherche intelligente |
| Memoire | mem_local_short | Synthese locale | Gratuit | |
| Memoire | nomem | Mode sans memoire | Gratuit | |

---

### Reconnaissance d'intention

| Type | Nom de la plateforme | Methode d'utilisation | Tarification | Notes |
|:------:|:-------------:|:----:|:-------:|:---------------------:|
| Intention | intent_llm | Appels via interface | Selon tarification LLM | Reconnaissance d'intention via grands modeles, forte generalisation |
| Intention | function_call | Appels via interface | Selon tarification LLM | Intention via appel de fonctions du LLM, rapide et efficace |
| Intention | nointent | Mode sans intention | Gratuit | Pas de reconnaissance d'intention, retourne directement le resultat du dialogue |

---

### RAG - Generation augmentee par recuperation

| Type | Nom de la plateforme | Methode d'utilisation | Tarification | Notes |
|:------:|:-------------:|:----:|:-------:|:---------------------:|
| RAG | ragflow | Appels via interface | Facturation selon les tokens consommes pour le decoupage et la segmentation | Utilise la fonctionnalite RAG de RagFlow pour fournir des reponses de dialogue plus precises |

---

## Remerciements

| Logo | Projet/Entreprise | Description |
|:---:|:---:|:---|
| <img src="./docs/images/logo_bailing.png" width="160"> | [Robot de dialogue vocal Bailing](https://github.com/wwbin2017/bailing) | Ce projet est inspire par le [Robot de dialogue vocal Bailing](https://github.com/wwbin2017/bailing) et developpe sur sa base |
| <img src="./docs/images/logo_tenclass.png" width="160"> | [Tenclass](https://www.tenclass.com/) | Merci a [Tenclass](https://www.tenclass.com/) pour l'elaboration des protocoles de communication standard, des solutions de compatibilite multi-appareils et des demonstrations de pratiques en haute concurrence pour l'ecosysteme Xiaozhi ; fourniture d'une documentation technique complete pour ce projet |
| <img src="./docs/images/logo_xuanfeng.png" width="160"> | [Xuanfeng Technology](https://github.com/Eric0308) | Merci a [Xuanfeng Technology](https://github.com/Eric0308) pour la contribution du framework d'appel de fonctions, du protocole de communication MCP et de l'implementation du mecanisme d'appel par plugins |
| <img src="./docs/images/logo_junsen.png" width="160"> | [huangjunsen](https://github.com/huangjunsen0406) | Merci a [huangjunsen](https://github.com/huangjunsen0406) pour la contribution du module `Console de controle intelligent Mobile`, permettant un controle efficace et une interaction en temps reel sur les appareils mobiles |
| <img src="./docs/images/logo_huiyuan.png" width="160"> | [Huiyuan Design](http://ui.kwd988.net/) | Merci a [Huiyuan Design](http://ui.kwd988.net/) pour les solutions visuelles professionnelles de ce projet |
| <img src="./docs/images/logo_qinren.png" width="160"> | [Xi'an Qinren Information Technology](https://www.029app.com/) | Merci a [Xi'an Qinren Information Technology](https://www.029app.com/) pour l'approfondissement du systeme visuel de ce projet |
| <img src="./docs/images/logo_contributors.png" width="160"> | [Contributeurs au code](https://github.com/xinnan-tech/xiaozhi-esp32-server/graphs/contributors) | Merci a [tous les contributeurs](https://github.com/xinnan-tech/xiaozhi-esp32-server/graphs/contributors), vos efforts ont rendu le projet plus robuste et puissant. |


<a href="https://star-history.com/#xinnan-tech/xiaozhi-esp32-server&Date">

 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xinnan-tech/xiaozhi-esp32-server&type=Date" />
 </picture>
</a>

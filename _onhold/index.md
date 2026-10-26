---
layout: archive
permalink: /
title:
---

## [Thoughts of Mine]({{ site.url }}/articles/)  

<div class="tiles">
{% for post in site.categories.blog limit:4 %}
  {% include post-grid.html %}
{% endfor %}
</div><p style="color:white">""</p>

## [Things to look at]({{ site.url }}/graphics/)

<div class="tiles">
{% for post in site.categories.graphics limit:5 %}
  {% include graphics-grid.html %}
{% endfor %}
</div>  




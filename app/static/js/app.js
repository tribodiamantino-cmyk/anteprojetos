(function () {
  const fieldEditor = document.getElementById("field-editor");
  const addFieldButton = document.getElementById("add-field-button");
  const fieldTemplate = document.getElementById("field-row-template");

  if (fieldEditor && addFieldButton && fieldTemplate) {
    function nextOrder() {
      return fieldEditor.querySelectorAll(".field-row").length + 1;
    }

    function bindRemove(button) {
      button.addEventListener("click", () => {
        button.closest(".field-row").remove();
      });
    }

    fieldEditor.querySelectorAll(".remove-field-button").forEach(bindRemove);

    addFieldButton.addEventListener("click", () => {
      const fragment = fieldTemplate.content.cloneNode(true);
      const ordem = fragment.querySelector("input[name='field_ordem']");
      if (ordem) {
        ordem.value = nextOrder();
      }
      fragment.querySelectorAll(".remove-field-button").forEach(bindRemove);
      fieldEditor.appendChild(fragment);
    });
  }
})();

(function () {
  const attributeEditor = document.getElementById("attribute-editor");
  const addAttributeButton = document.getElementById("add-attribute-button");
  const attributeTemplate = document.getElementById("attribute-row-template");

  if (!attributeEditor || !addAttributeButton || !attributeTemplate) return;

  function slug(value) {
    return (value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || "atributo";
  }

  function rows() {
    return Array.from(attributeEditor.querySelectorAll("[data-attribute-row]"));
  }

  function reindex() {
    rows().forEach((row, index) => {
      const ordem = row.querySelector("input[name='attr_ordem']");
      const obrigatorio = row.querySelector("input[name='attr_obrigatorio']");
      const resumo = row.querySelector("input[name='attr_visivel_resumo']");
      const title = row.querySelector(".atributo-card-header strong");
      if (title) {
        title.textContent = `Atributo tecnico #${index + 1}`;
      }
      if (ordem && !ordem.value) {
        ordem.value = index + 1;
      }
      if (obrigatorio) {
        obrigatorio.value = String(index);
      }
      if (resumo) {
        resumo.value = String(index);
      }
    });
  }

  function bindRow(row) {
    const nome = row.querySelector("input[name='attr_nome']");
    const chave = row.querySelector("input[name='attr_chave']");
    const remove = row.querySelector(".remove-attribute-button");

    if (nome && chave) {
      nome.addEventListener("input", () => {
        if (!chave.dataset.edited) {
          chave.value = slug(nome.value);
        }
      });
      chave.addEventListener("input", () => {
        chave.dataset.edited = "true";
        chave.value = slug(chave.value);
      });
    }

    if (remove) {
      remove.addEventListener("click", () => {
        row.remove();
        reindex();
      });
    }
  }

  rows().forEach(bindRow);
  reindex();

  addAttributeButton.addEventListener("click", () => {
    const fragment = attributeTemplate.content.cloneNode(true);
    const row = fragment.querySelector("[data-attribute-row]");
    attributeEditor.appendChild(fragment);
    bindRow(row);
    reindex();
  });
})();

(function () {
  const tipoObraSelect = document.getElementById("tipo-obra");

  function currentTipoObra() {
    return tipoObraSelect ? tipoObraSelect.value : window.ANTEPROJETO_TIPO_OBRA;
  }

  function situacaoOptions() {
    if (currentTipoObra() === "Obra nova") {
      return ["Novo"];
    }
    return ["Novo", "Existente", "Substituir", "Adequar", "Remover"];
  }

  function renderSituacao(select) {
    const atual = select.dataset.current || "";
    select.innerHTML = "";

    situacaoOptions().forEach((opcao) => {
      const option = document.createElement("option");
      option.value = opcao;
      option.textContent = opcao;
      option.selected = (atual && atual === opcao) || (!atual && opcao === "Novo");
      select.appendChild(option);
    });
  }

  document.querySelectorAll(".situacao-select").forEach(renderSituacao);

  if (tipoObraSelect) {
    tipoObraSelect.addEventListener("change", () => {
      document.querySelectorAll(".situacao-select").forEach((select) => {
        select.dataset.current = "";
        renderSituacao(select);
      });
    });
  }
})();

(function () {
  const form = document.getElementById("cascade-equipment-form");
  if (!form) return;

  const selects = [
    document.getElementById("equipamento-nivel-0"),
    document.getElementById("equipamento-nivel-1"),
    document.getElementById("equipamento-nivel-2"),
  ];
  const finalInput = document.getElementById("equipamento-final-id");
  const pathBox = document.getElementById("equipamento-caminho-selecionado");
  const attrsBox = document.getElementById("equipamento-atributos-carregados");
  const selectedChain = window.ITEM_EDITANDO_CADEIA || [];

  function resetSelect(select, placeholder) {
    select.innerHTML = "";
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    select.appendChild(option);
    select.disabled = true;
  }

  function setOptions(select, items, selectedId) {
    const placeholder = select.dataset.placeholder || "Selecione";
    resetSelect(select, placeholder);
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.nome;
      option.selected = String(selectedId || "") === String(item.id);
      select.appendChild(option);
    });
    select.disabled = items.length === 0;
  }

  async function fetchJson(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Falha ao carregar dados");
    return response.json();
  }

  function selectedPath() {
    return selects
      .filter((select) => select.value)
      .map((select) => select.options[select.selectedIndex].textContent);
  }

  function updatePath() {
    const path = selectedPath();
    pathBox.textContent = path.length ? path.join(" > ") : "";
  }

  function renderAttributes(attrs) {
    attrsBox.innerHTML = "";
    if (!attrs.length) {
      attrsBox.innerHTML = '<p class="muted">Nenhum atributo tecnico cadastrado para este item.</p>';
      return;
    }

    const title = document.createElement("h3");
    title.textContent = "Dados carregados";
    attrsBox.appendChild(title);

    const list = document.createElement("dl");
    list.className = "loaded-attributes-grid";
    attrs.forEach((attr) => {
      const item = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = attr.nome;
      const value = attr.valor || "-";
      dd.textContent = attr.unidade ? `${value} ${attr.unidade}` : value;
      item.appendChild(dt);
      item.appendChild(dd);
      list.appendChild(item);
    });
    attrsBox.appendChild(list);
  }

  async function loadAttributes(equipmentId) {
    if (!equipmentId) {
      attrsBox.innerHTML = "";
      return;
    }
    const attrs = await fetchJson(`/equipamentos/${equipmentId}/atributos`);
    renderAttributes(attrs);
  }

  async function loadChildren(level, parentId, selectedId) {
    const next = selects[level + 1];
    if (!next) return [];
    resetSelect(next, next.dataset.placeholder || "Selecione");
    for (let index = level + 2; index < selects.length; index += 1) {
      resetSelect(selects[index], selects[index].dataset.placeholder || "Selecione");
    }
    if (!parentId) return [];

    const children = await fetchJson(`/equipamentos/${parentId}/filhos`);
    setOptions(next, children, selectedId);
    return children;
  }

  async function chooseLevel(level) {
    const selectedId = selects[level].value;
    finalInput.value = "";
    attrsBox.innerHTML = "";

    if (!selectedId) {
      for (let index = level + 1; index < selects.length; index += 1) {
        resetSelect(selects[index], selects[index].dataset.placeholder || "Selecione");
      }
      updatePath();
      return;
    }

    const children = await loadChildren(level, selectedId);
    if (!children.length || level === selects.length - 1) {
      finalInput.value = selectedId;
      await loadAttributes(selectedId);
    }
    updatePath();
  }

  selects.forEach((select, level) => {
    select.addEventListener("change", () => {
      chooseLevel(level).catch(() => {
        attrsBox.innerHTML = '<p class="muted">Nao foi possivel carregar os dados do equipamento.</p>';
      });
    });
  });

  form.addEventListener("submit", (event) => {
    if (!finalInput.value) {
      event.preventDefault();
      attrsBox.innerHTML = '<p class="muted">Selecione o modelo final antes de adicionar ao anteprojeto.</p>';
    }
  });

  async function preloadSelection() {
    if (!selectedChain.length) return;
    selects[0].value = selectedChain[0].id;
    if (selectedChain[1]) {
      await loadChildren(0, selectedChain[0].id, selectedChain[1].id);
    }
    if (selectedChain[2]) {
      await loadChildren(1, selectedChain[1].id, selectedChain[2].id);
      finalInput.value = selectedChain[selectedChain.length - 1].id;
      await loadAttributes(finalInput.value);
    } else if (selectedChain[1]) {
      finalInput.value = selectedChain[1].id;
      await loadAttributes(finalInput.value);
    } else {
      finalInput.value = selectedChain[0].id;
      await loadAttributes(finalInput.value);
    }
    updatePath();
  }

  preloadSelection().catch(() => {});
})();

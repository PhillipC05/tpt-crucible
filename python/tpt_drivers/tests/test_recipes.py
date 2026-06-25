"""Tests for recipe system."""

from pathlib import Path
import json

from tpt_drivers.recipes import Recipe, RecipeStep, RecipeManager, BUILTIN_RECIPES


class TestRecipe:
    def test_to_dict_roundtrip(self):
        recipe = Recipe(
            name="test-recipe",
            description="Test deployment",
            model_id="test/model",
            hardware_type="swarm",
            node_count=8,
            topology="ring",
            steps=[RecipeStep(name="ingest", action="tpt-catalyst ingest model.pt")],
            drivers=["esp32-devkit"],
        )
        d = recipe.to_dict()
        restored = Recipe.from_dict(d)
        assert restored.name == "test-recipe"
        assert restored.node_count == 8
        assert len(restored.steps) == 1

    def test_save_and_load(self, tmp_path):
        recipe = Recipe(
            name="test", description="test", model_id="m",
            hardware_type="swarm", node_count=4, topology="grid2d",
            steps=[RecipeStep(name="s1", action="cmd1")],
        )
        path = tmp_path / "test.json"
        recipe.save(path)
        loaded = Recipe.load(path)
        assert loaded.name == "test"


class TestBuiltinRecipes:
    def test_recipes_exist(self):
        assert len(BUILTIN_RECIPES) >= 3

    def test_tinyllama_recipe(self):
        recipe = next(r for r in BUILTIN_RECIPES if r.name == "tinyllama-esp32-16node")
        assert recipe.node_count == 16
        assert recipe.hardware_type == "swarm"
        assert len(recipe.steps) >= 4


class TestRecipeManager:
    def test_list_recipes(self, tmp_path):
        manager = RecipeManager(recipes_dir=tmp_path)
        recipes = manager.list_recipes()
        assert len(recipes) >= 3

    def test_get_recipe(self, tmp_path):
        manager = RecipeManager(recipes_dir=tmp_path)
        recipe = manager.get_recipe("tinyllama-esp32-16node")
        assert recipe is not None
        assert recipe.model_id == "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"

    def test_search(self, tmp_path):
        manager = RecipeManager(recipes_dir=tmp_path)
        results = manager.search("esp32")
        assert len(results) >= 1

    def test_save_custom_recipe(self, tmp_path):
        manager = RecipeManager(recipes_dir=tmp_path)
        recipe = Recipe(
            name="custom-test", description="Custom", model_id="m",
            hardware_type="swarm", node_count=4, topology="grid2d",
            steps=[RecipeStep(name="s1", action="cmd1")],
        )
        path = manager.save_recipe(recipe)
        assert path.exists()
        loaded = manager.get_recipe("custom-test")
        assert loaded is not None

class Gloom < Formula
  include Language::Python::Virtualenv

  desc "High-performance CLI for Google Cloud Context & ADC Switching"
  homepage "https://github.com/hilmanmustofaa/gloom"
  url "https://files.pythonhosted.org/packages/source/g/gloom-cli/gloom-cli-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256_AFTER_PYPI_PUBLISH"
  license "MIT"
  head "https://github.com/hilmanmustofaa/gloom.git", branch: "main"

  depends_on "python@3.11"

  resource "typer" do
    url "https://files.pythonhosted.org/packages/source/t/typer/typer-0.9.0.tar.gz"
    sha256 "50922fd79ber3f6f84f..." # Update with actual sha256
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.7.0.tar.gz"
    sha256 "..." # Update with actual sha256
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic/pydantic-2.5.0.tar.gz"
    sha256 "..." # Update with actual sha256
  end

  resource "pydantic-settings" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic-settings/pydantic_settings-2.1.0.tar.gz"
    sha256 "..." # Update with actual sha256
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "gloom version", shell_output("#{bin}/gloom --version")
    assert_match "No cached contexts", shell_output("#{bin}/gloom list")
  end
end

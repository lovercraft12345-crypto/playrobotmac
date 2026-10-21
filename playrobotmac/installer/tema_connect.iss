; Interfaz personalizada; Inno Setup conserva copia, desinstalación y validación.
[Code]
var
  Fondo: TBitmapImage;
  Titulo, Descripcion, DatoTitulo, Dato, Porcentaje: TLabel;
  Ruta: TNewEdit;
  Buscar: TNewButton;
  Abrir: TNewCheckBox;
  UltimoDato: Integer;

function Texto(X, Y, W, H, Tam: Integer; Negrita: Boolean): TLabel;
begin
  Result := TLabel.Create(WizardForm);
  Result.Parent := WizardForm;
  Result.SetBounds(ScaleX(X), ScaleY(Y), ScaleX(W), ScaleY(H));
  Result.AutoSize := False;
  Result.WordWrap := True;
  Result.Transparent := True;
  Result.Font.Name := 'Comic Sans MS';
  Result.Font.Size := Tam;
  Result.Font.Color := $00252525;
  if Negrita then Result.Font.Style := [fsBold];
end;

procedure MostrarDato(Indice: Integer);
begin
  case Indice mod 5 of
    0: Dato.Caption := 'Un programa es una secuencia de instrucciones. Cada engrane de PlayRobot representa una acción.';
    1: Dato.Caption := 'Un ciclo permite repetir instrucciones. ¡Prueba encender y apagar un LED varias veces!';
    2: Dato.Caption := 'Los sensores ayudan a un robot a conocer lo que ocurre a su alrededor.';
    3: Dato.Caption := 'Puedes probar tu receta en la simulación antes de enviarla a la ESP32.';
    4: Dato.Caption := 'Los engranes conectados a Comenzar forman tu programa. Los engranes sueltos no se ejecutan.';
  end;
end;

procedure ElegirCarpeta(Sender: TObject);
var Carpeta: String;
begin
  Carpeta := Ruta.Text;
  if BrowseForFolder('Elige dónde instalar PlayRobot', Carpeta, False) then
    Ruta.Text := Carpeta;
end;

procedure CambiarAbrir(Sender: TObject);
begin
  if WizardForm.RunList.Items.Count > 0 then
    WizardForm.RunList.Checked[0] := Abrir.Checked;
end;

procedure InitializeWizard;
begin
  WizardForm.ClientWidth := ScaleX(904);
  WizardForm.ClientHeight := ScaleY(620);
  WizardForm.Position := poScreenCenter;
  WizardForm.Color := $0043E9F6;
  WizardForm.Caption := 'PlayRobot Connect · Instalación';
  WizardForm.Font.Name := 'Segoe UI';
  WizardForm.OuterNotebook.Visible := False;
  WizardForm.Bevel.Visible := False;
  WizardForm.Bevel1.Visible := False;
  WizardForm.BeveledLabel.Visible := False;

  ExtractTemporaryFile('fondo_connect.bmp');
  Fondo := TBitmapImage.Create(WizardForm);
  Fondo.Parent := WizardForm;
  Fondo.SetBounds(0, 0, ScaleX(904), ScaleY(570));
  Fondo.Stretch := True;
  Fondo.Bitmap.LoadFromFile(ExpandConstant('{tmp}\fondo_connect.bmp'));
  Fondo.SendToBack;

  Titulo := Texto(388, 235, 470, 42, 18, True);
  Descripcion := Texto(388, 292, 350, 120, 11, False);
  DatoTitulo := Texto(388, 355, 350, 40, 16, True);
  DatoTitulo.Caption := '¿SABÍAS QUE...?';
  Dato := Texto(388, 405, 335, 140, 12, True);
  Porcentaje := Texto(388, 327, 470, 25, 10, False);
  UltimoDato := -1;

  Ruta := TNewEdit.Create(WizardForm);
  Ruta.Parent := WizardForm;
  Ruta.SetBounds(ScaleX(388), ScaleY(305), ScaleX(350), ScaleY(30));
  Ruta.Font.Name := 'Segoe UI';
  Ruta.Font.Size := 10;
  Ruta.Text := WizardForm.DirEdit.Text;
  Buscar := TNewButton.Create(WizardForm);
  Buscar.Parent := WizardForm;
  Buscar.SetBounds(ScaleX(748), ScaleY(305), ScaleX(108), ScaleY(30));
  Buscar.Caption := 'Buscar...';
  Buscar.OnClick := @ElegirCarpeta;

  WizardForm.ProgressGauge.Parent := WizardForm;
  WizardForm.ProgressGauge.SetBounds(ScaleX(388), ScaleY(288), ScaleX(478), ScaleY(30));
  WizardForm.BackButton.SetBounds(ScaleX(542), ScaleY(578), ScaleX(104), ScaleY(32));
  WizardForm.NextButton.SetBounds(ScaleX(656), ScaleY(578), ScaleX(116), ScaleY(32));
  WizardForm.CancelButton.SetBounds(ScaleX(782), ScaleY(578), ScaleX(104), ScaleY(32));
  WizardForm.BackButton.BringToFront;
  WizardForm.NextButton.BringToFront;
  WizardForm.CancelButton.BringToFront;
  Abrir := TNewCheckBox.Create(WizardForm);
  Abrir.Parent := WizardForm;
  Abrir.SetBounds(ScaleX(388), ScaleY(445), ScaleX(330), ScaleY(28));
  Abrir.Caption := 'Abrir PlayRobot al terminar';
  Abrir.Checked := True;
  Abrir.OnClick := @CambiarAbrir;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpInfoBefore) or (PageID = wpSelectTasks) or
    (PageID = wpReady) or (PageID = wpSelectProgramGroup);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    if Trim(Ruta.Text) = '' then
    begin
      MsgBox('Elige una carpeta para instalar PlayRobot.', mbError, MB_OK);
      Result := False;
    end
    else WizardForm.DirEdit.Text := Trim(Ruta.Text);
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  WizardForm.OuterNotebook.Visible := CurPageID = wpPreparing;
  Titulo.Visible := CurPageID <> wpPreparing;
  Ruta.Visible := CurPageID = wpSelectDir;
  Buscar.Visible := Ruta.Visible;
  Abrir.Visible := CurPageID = wpFinished;
  WizardForm.ProgressGauge.Visible := CurPageID = wpInstalling;
  Porcentaje.Visible := CurPageID = wpInstalling;
  DatoTitulo.Visible := CurPageID = wpInstalling;
  Dato.Visible := CurPageID = wpInstalling;
  Descripcion.Visible := CurPageID <> wpInstalling;
  case CurPageID of
    wpWelcome:
      begin
        Titulo.Caption := '¡Tu aventura empieza aquí!';
        Descripcion.Caption := 'Aprende programación, arma engranes y crea con tu ESP32.' + #13#10 + #13#10 +
          'Vamos a instalar PlayRobot y todo su entorno. Pulsa Siguiente para comenzar.';
        WizardForm.NextButton.Caption := 'Siguiente >';
      end;
    wpSelectDir:
      begin
        Titulo.Caption := '¿Dónde lo instalamos?';
        Descripcion.SetBounds(ScaleX(388), ScaleY(365), ScaleX(330), ScaleY(130));
        Descripcion.Caption := 'Si deseas cambiar la ubicación, pulsa Buscar. Después pulsa Instalar para confirmar.';
        WizardForm.NextButton.Caption := 'Instalar';
      end;
    wpPreparing:
      begin
        Titulo.Visible := False;
        Descripcion.Visible := False;
      end;
    wpInstalling:
      begin
        Titulo.Caption := 'Instalando...';
        Porcentaje.Caption := 'Preparando PlayRobot...';
        MostrarDato(0);
      end;
    wpFinished:
      begin
        Titulo.Caption := '¡Todo listo para crear!';
        Descripcion.SetBounds(ScaleX(388), ScaleY(300), ScaleX(330), ScaleY(120));
        Descripcion.Caption := 'PlayRobot ya está instalado.' + #13#10 + #13#10 +
          'También puedes abrirlo desde el escritorio o el menú Inicio.';
        WizardForm.NextButton.Caption := 'Finalizar';
        CambiarAbrir(Abrir);
      end;
  end;
  if CurPageID = wpWelcome then
    Descripcion.SetBounds(ScaleX(388), ScaleY(292), ScaleX(350), ScaleY(185));
end;

procedure CurInstallProgressChanged(CurProgress, MaxProgress: Integer);
var P, Indice: Integer;
begin
  if MaxProgress <= 0 then Exit;
  P := Round(100.0 * CurProgress / MaxProgress);
  Porcentaje.Caption := IntToStr(P) + '% · Instalando archivos y componentes';
  Indice := P div 20;
  if Indice <> UltimoDato then
  begin
    MostrarDato(Indice);
    UltimoDato := Indice;
  end;
end;

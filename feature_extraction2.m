% This function is a revised version of COVAREP_feature_extraction.m in the original COVAREP package.


function feature_extraction2(file,sample_rate)

addpath(genpath('/usr/local/covarep'));
addpath(genpath('/usr/local/sap-voicebox'));

%% Initial settings
if nargin < 2
    sample_rate=0.01; % Default to 10 ms sampling
end

basename=regexp(file,'\.wav','split');
basename=char(basename(1));

% F0 settings
F0min = 80; % Minimum F0 set to 80 Hz
F0max = 400; % Maximum F0 set to 500 Hz

% IAIF settings
hpfilt = 1;
d = 0.99;

% LP settings
LP_winLen=0.025;
LP_winShift=0.005;

% Rd MSP settings
opt = sin_analysis();
opt.fharmonic  = true;
opt.use_ls     = false;
opt.debug = 0;

% Envelope settings
opt.use_ls     = false; % Use Peak Picking
opt.dftlen     = 4096;  % Force the DFT length
opt.frames_keepspec = true; % Keep the computed spectra in the frames structure
MCEP_ord=24;

% Analysis settings
%names={'F0','VUV','NAQ','QOQ','H1H2', 'PSP', 'peakSlope','creak', 'HMPDM_0','HMPDM_1','HMPDM_2','HMPDM_3','HMPDM_4','HMPDM_5', ...
%    'HMPDM_6','HMPDM_7','HMPDM_8','HMPDM_9','HMPDM_10','HMPDM_11','HMPDM_12', ...
%    'HMPDM_13','HMPDM_14','HMPDM_15','HMPDM_16','HMPDM_17','HMPDM_18', ...
%    'HMPDM_19','HMPDM_20','HMPDM_21','HMPDM_22','HMPDM_23','HMPDM_24',...
%    'HMPDD_0','HMPDD_1','HMPDD_2','HMPDD_3','HMPDD_4','HMPDD_5', ...
%    'HMPDD_6','HMPDD_7','HMPDD_8','HMPDD_9','HMPDD_10','HMPDD_11','HMPDD_12'};
names={'F0','VUV','NAQ','QOQ','H1H2','PSP','MDQ','peakSlope','creak'};

%% Do processing
try
    % Load file and set sample locations
    [x,fs]=audioread(file);
    feature_sampling=round((sample_rate/2)*fs):round(sample_rate*fs):length(x);
        
    % Polarity detection
    polarity = polarity_reskew(x,fs);
    x=polarity*x; % Correct polarity if necessary

    % F0/GCI detection 
    [srh_f0,srh_vuv,~,srh_time] = pitch_srh(x,fs,F0min,F0max, 10); %setting window size of 10 ms
    F0med=median(srh_f0(srh_f0>F0min&srh_f0<F0max&srh_vuv==1));
    F0 = interp1(round(srh_time*fs),srh_f0,feature_sampling);
    VUV = interp1(round(srh_time*fs),srh_vuv,feature_sampling);
    VUV_int = interp1(round(srh_time*fs),srh_vuv,1:length(x));
    VUV(isnan(VUV)==1)=0; VUV_int(isnan(VUV_int)==1)=0; 
    VUV(VUV>=.5)=1; VUV(VUV<.5)=0;

    GCI = gci_sedreams(x,fs,F0med,1); % SEDREAMS GCI detection
    GCI=round(GCI*fs); GCI(GCI<1|isnan(GCI)==1|isinf(GCI)==1)=[];
    GCI(VUV_int(GCI)<.5)=[]; % Remove GCIs in detected unvoiced regions
    GCI=unique(GCI); % Remove possible duplications

    % Iterative and adaptive inverse filtering (IAIF) & LP inverse
    % filtering
    p_gl = 2*round(fs/4000);
    p_vt = 2*round(fs/2000)+4;
    [g_iaif,gd_iaif] = iaif_gci(x,fs,GCI/fs,p_vt,p_gl,d,hpfilt);
    res = lpcresidual(x,LP_winLen*fs,LP_winShift*fs,fs/1000+2); % LP residual

    % Glottal source parameterisation
    [NAQ,QOQ,H1H2,HRF,PSP] = get_vq_params(g_iaif,gd_iaif,fs,GCI/fs); % Estimate conventional glottal parameters

    % Wavelet-based parameters
    MDQ = mdq(res,fs,GCI/fs); % Maxima dispersion quotient measurement
    PS = peakslope(x,fs);   % peakSlope extraction
    MDQ=interp1(MDQ(:,1)*fs,MDQ(:,2),feature_sampling);
    PS=interp1(PS(:,1)*fs,PS(:,2),feature_sampling);

    % Rd parameter estimation of the LF glottal model using Mean Squared Phase (MSP)
    %srh_f0(srh_f0==0) = 100;
    %frames = sin_analysis(x, fs, [srh_time(:),srh_f0(:)], opt);
    %rds = rd_msp(frames, fs);

    % Creaky voice detection
    warning off
    try
        creak_pp = detect_creaky_voice(x,fs); % Detect creaky voice
        creak_pp=interp1(creak_pp(:,2),creak_pp(:,1),feature_sampling);
    catch
        creak_pp=zeros(length(feature_sampling),1);
    end
    warning on

    % Spectral envelope parameterisation
    %M=numel(frames);
    %MCEP=zeros(M,MCEP_ord+1);
    %TE_orders = round(0.5*fs./[frames.f0]); % optimal cepstral order
    %spec = hspec2spec(vertcat(frames.S));
    %TE_orders_unique = unique(TE_orders);
    %for m=1:numel(TE_orders_unique)
    %    idx = TE_orders_unique(m)==TE_orders;
    %    MCEP(idx,:) = hspec2fwcep(env_te(spec(idx,:), TE_orders_unique(m))',...
    %        fs, MCEP_ord)';
    %end

    % Interpolate features to feature sampling rate
    NAQ=interp1(NAQ(:,1)*fs,NAQ(:,2),feature_sampling);
    QOQ=interp1(QOQ(:,1)*fs,QOQ(:,2),feature_sampling);
    H1H2=interp1(H1H2(:,1)*fs,H1H2(:,2),feature_sampling);
    PSP=interp1(PSP(:,1)*fs,PSP(:,2),feature_sampling);
    %Rd=interp1(rds(:,1)*fs,rds(:,2),feature_sampling);
    %Rd_conf=interp1(rds(:,1)*fs,rds(:,3),feature_sampling);

    %MCEP_int=zeros(length(feature_sampling),MCEP_ord+1);
    %for m=1:MCEP_ord+1
    %   MCEP_int(:,m) = interp1(round(linspace(1,length(x),size(MCEP,1))),MCEP(:,m),feature_sampling);
    %end

    % Add PDM and PDD
    %hmpdopt = hmpd_analysis();
    %hmpdopt.debug = 0;
    %hmpdopt.usemex = false;
    %hmpdopt.amp_enc_method=2; hmpdopt.amp_log=true; hmpdopt.amp_order=39;
    %hmpdopt.pdd_log=true; hmpdopt.pdd_order=12;% MFCC-like phase variance
    %hmpdopt.pdm_log=true; hmpdopt.pdm_order=24;% Number of log-Harmonic coefs
    %[hmpdf0s, ~, HMPDM, HMPDD] = hmpd_analysis_features(frames, fs, hmpdopt);
    %HMPDM = irregsampling2uniformsampling(hmpdf0s(:,1), HMPDM, (feature_sampling-1)/fs, @unwrap, @wrap, 'linear', 0, hmpdopt.usemex);
    %HMPDD = irregsampling2uniformsampling(hmpdf0s(:,1), HMPDD, (feature_sampling-1)/fs, [], [], 'linear', 0, hmpdopt.usemex);

    % Create feature matrix and save

    %features=[F0(:) VUV(:) NAQ(:) QOQ(:) H1H2(:) PSP(:) PS(:) creak_pp(:)]
    features=[F0(:) VUV(:) NAQ(:) QOQ(:) H1H2(:) PSP(:) MDQ(:) PS(:) creak_pp(:)];
    %features(isnan(features))=0;
    
    writecell(names, [basename '.dat'], "Delimiter","tab", "QuoteStrings",0);
    writematrix(features, [basename '.dat'], "Delimiter","tab", "WriteMode","append");
    clear features

    disp([basename ' successfully analysed'])


catch err
    warning(['An error occurred while analysing ' basename ': ' getReport(err)])
end

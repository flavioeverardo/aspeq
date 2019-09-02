%% eq.lp
%% This program proposes different equalization configurations for all tracks.
%% Eq should be applied only to tracks that share panning positions (left, center, right). To be done, panning + EQ
%% ASP as a cross-adaptive method for multitrack mixing
%% Eq attempts to achieve equal average loudness across all frequency bands of all tracks

%% Tracks levels convertion
% PowerRatio  Linear Amp      dBFS
%  100         1							   0
%   81				 0.9						 - 0.4
%   64				 0.8						 - 1.0
%   49				 0.7						 - 3.1
%   36				 0.6						 - 4.4
%   25				 0.5						 - 6.0
%   16				 0.4						 - 8.0
%    9				 0.3						 -10.5
%    4         0.2						 -14.0
%    1         0.1						 -20.0


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Encoding

%% Find shared (essential) bands
shared_band(I1,B) :- essential_band(I1,B), essential_band(I2,B), I1 != I2.

%% If exist shared essential band... choose only one
1 { _essential_band(I,B) : shared_band(I,B) } 1.% :- shared_band(I1,B), shared_band(I2,B), I1 != I2.
%% Else, there is no conflict with the essential bands
_essential_band(I,B) :- not shared_band(I,B), essential_band(I,B).

%% Get all the tracks from the erb atoms
%track(I) :- erb_band(I,_,_).

%% Band detected to be Eqd... This must be part of the instance
eq_band(B) :- _essential_band(_,B).

%% Linear amplitude values to boost or to cut. The amplitude domain to be discussed.
amplitude(10;20;30;40;50;60;70;80;90).

%% Masking threshold. Max 0.9, Min 0.3 *100
%% The lower the value, more processing between tracks. Use lower values when trying to clean more the mix.
%% The higher the value, less processing between tracks. Use higher values when trying to get a more busy mix.
%#const masking_factor = 50. 

%% The max points become maskee points, so for each other track that share the same frequency band, determine if exist a masker.
%% Masking is defined if an amplitude of 1 minus the sum of the masker and the maskee results  greater than the masking threshold constant.
masking_coefficient(B,Masker,Maskee,100-(|P1-P2|)) :- _essential_band(Maskee,B), eq_band(B), erb_band(Masker,B,P1), erb_band(Maskee,B,P2), Masker != Maskee.

%% Get the masker and the maskee per frequency band if the masking coefficient value is greater or equal the masking factor
%% Masker masks the Maskee at frequency F.
mask(Masker,Maskee,B) :- masking_coefficient(B,Masker,Maskee,S), S >= masking_factor. 

%% The code after this point is executed if exist at least one masking issue.!!!!!!!!!!!!!!!!!!!!!!!!!!!
%% Tracks involved in the masking process after the masking coefficient is calculated
%mask(Masker,B) :- mask(Masker,Maskee,B).
%mask(Maskee,B) :- mask(Masker,Maskee,B).

%% If exist masking... Find another configuration for Masker and Maskee
%% This new configuration can cut the masker, boost the maskee or both (mirror eq).
1 { cut_masker(Masker,B) ; boost_maskee(Maskee,B) } 2 :- mask(Masker,Maskee,B), erb_band(Masker,B,P).

%% Cut the masker and boost the maskee
1 {   cut(Masker,B, P, P-( P-A ),  P-A ) : amplitude(A) } 1 :- erb_band(Masker,B,P), mask(Masker,Maskee,B),   cut_masker(Masker,B).
1 { boost(Maskee,B, P, |P-A|, P+(|P-A|)) : amplitude(A) } 1 :- erb_band(Maskee,B,P), mask(Masker,Maskee,B), boost_maskee(Maskee,B).

%% In other words, propose new amplitude levels for the masker and the maskee.
%% Propose less amplitude for the masker and higher for the maskee
%% The goal is to propose new amplitudes per band without changing the intensity of the frequency band
freq_band_amplitude(Masker,B,A) :-    cut(Masker,B,P,C,A), mask(Masker,_,B).
freq_band_amplitude(Maskee,B,A) :-  boost(Maskee,B,P,C,A), mask(_,Maskee,B).

%% By pass the non eqd tracks per essential frequency band
%% This rule comes from tracks not involved in the masking process
freq_band_amplitude(M,B,P) :- erb_band(M,B,P), not   cut_masker(M,B); not boost_maskee(M,B), eq_band(B).%, mask(M,B).

%% Check the masking coefficient per band after equalization 
masking_coefficient_after_eq(B,Masker,Maskee,100-(|P1-P2|)) :- eq_band(B), freq_band_amplitude(Masker,B,P1), freq_band_amplitude(Maskee,B,P2), mask(Masker,Maskee,B), Masker != Maskee.

%% Masking still occurs after eq?
%% Constraint only to answers that do not mask after eq
:- masking_coefficient_after_eq(B,Masker,Maskee,S), S >= masking_factor.

%% Not valid negative cuts
:- cut(_,_,_,_,RP), RP <= 0.
%% Not valid boost above 100 or 1.0 linear amplitude
:- boost(_,_,_,_,RP), RP > 100.


%#show essential_band/2.
%#show shared_band/2.
#show _essential_band/2.
#show mask/3.
#show cut/5.
#show boost/5.
%#show freq_band_amplitude/3.
%#show masking_coefficient/4.
%#show masking_coefficient_after_eq/4.
